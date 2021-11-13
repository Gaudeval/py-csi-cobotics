"""Experiment wrapper to run digital twin simulations"""

import json
import pickle
import shutil
import subprocess

from pathlib import Path
from typing import List, Iterable, Dict, Tuple

from csi.configuration import ConfigurationManager
from csi.coverage import EventCombinationsRegistry, Domain
from csi.experiment import Experiment
from csi.monitor import Trace, Monitor
from csi.safety import SafetyCondition
from csi.twin import DataBase, DigitalTwinConfiguration
from csi.twin.importer import from_table

from .monitor import SafetyControllerStatus, Notif, Act, Loc, RngDet, SafMod, Phase
from .uc import SafetyUseCase, U1, U2, MU
from .validation import predicates


class DigitalTwinRunner(Experiment):
    """Digital twin experiment runner"""

    safety_conditions: List[SafetyCondition]
    configuration: DigitalTwinConfiguration

    configuration_output: Path = Path("assets/configuration.json")
    database_output: Path = Path("assets/database.sqlite")
    screenshot_output: Path = Path("assets/screenshots/")
    trace_output: Path = Path("events_trace.pkl")

    additional_output: Dict[str, Tuple[Path, Path]] = {}

    def clear_build_output(self):
        """Cleanup generated files in build folder"""
        self.configuration.build.configuration.unlink(missing_ok=True)
        self.configuration.build.database.unlink(missing_ok=True)
        shutil.rmtree(self.configuration.build.screenshots, ignore_errors=True)
        for (removed, _) in self.additional_output.values():
            (self.configuration.build.path / removed).unlink(missing_ok=True)

    def collect_build_output(self):
        """Collect generated files in build folder"""
        self.database_output.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(self.configuration.build.database, self.database_output)
        self.configuration_output.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(self.configuration.build.configuration, self.configuration_output)
        self.screenshot_output.parent.mkdir(parents=True, exist_ok=True)
        if self.configuration.build.screenshots.exists():
            shutil.copytree(
                self.configuration.build.screenshots,
                self.screenshot_output,
                dirs_exist_ok=True,
            )
        for (saved, backup) in self.additional_output.values():
            if (self.configuration.build.path / saved).exists():
                backup.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy(saved, backup)

    def execute(self) -> None:
        """Run digital twin build with specified configuration"""
        # Setup build and IO
        database_path = self.configuration.build.configuration
        executable_path = self.configuration.build.path / "Unity.exe"
        configuration_path = self.configuration.build.configuration
        self.clear_build_output()
        # Setup configuration
        if not configuration_path.parent.exists():
            configuration_path.parent.mkdir(parents=True, exist_ok=True)
        ConfigurationManager().save(self.configuration.world, configuration_path)
        # Run Unity build
        try:
            subprocess.run(str(executable_path), shell=True, check=True)
        finally:
            self.collect_build_output()
        # Check for hazard occurrence
        trace, conditions = self.process_output()
        self.produce_safety_report(trace, conditions)
        # Backup processed trace
        with self.trace_output.open("wb") as trace_file:
            pickle.dump(trace, trace_file)

    def produce_safety_report(self, trace, conditions, quiet=False):
        report = {}
        safety_condition: SafetyCondition
        for safety_condition in conditions:
            i = Monitor().evaluate(
                trace,
                safety_condition.condition,
                dt=0.01,
                quantitative=self.configuration.ltl.quantitative,
                logic=self.configuration.ltl.logic,
            )
            if not quiet:
                print(type(safety_condition), safety_condition.uid)
                print(getattr(safety_condition, "description", ""))
                print("Occurs: ", i)
            report[safety_condition.uid] = i
        with open("./hazard-report.json", "w") as json_report:
            json.dump(report, json_report, indent=4)
        return report

    def process_output(self) -> Tuple[Trace, List[SafetyCondition]]:
        raise NotImplementedError


class SafetyDigitalTwinRunner(DigitalTwinRunner):
    safety_conditions: List[SafetyCondition] = predicates

    use_cases: List[SafetyUseCase] = [U1, U2, MU]
    use_cases_classification: Path = Path("uc-classification.json")
    use_cases_events: Path = Path("uc-events_combinations.pkl")

    event_combinations_output: Path = Path("events_combinations.pkl")

    def classify_use_cases(self, trace):
        """Classify trace use case"""
        ucs = [u for u in self.use_cases if u.satisfies(trace)]
        with self.use_cases_classification.open("w") as uc_output:
            json.dump([u.name for u in ucs], uc_output, indent=4)
        return ucs

    def build_event_trace(self, db: DataBase) -> Trace:
        """Extract event stream from run message stream"""
        # Prepare trace
        trace = Trace()
        P = SafetyControllerStatus()

        # notif
        trace[P.notif] = (0.0, Notif.ok)
        for m in from_table(db, "operatorinteraction"):
            trace[P.notif] = (m.timestamp, Notif(m.status))

        # ract / wact
        trace[P.ract] = (0.0, Act.exchWrkp)
        trace[P.wact] = (0.0, Act.idle)
        for m in from_table(db, "actstatus"):
            s = Act(m.status)
            if m.topic == "cobot/mode/update":
                trace[P.ract] = (m.timestamp, s)
            elif m.topic == "welder/mode/update":
                trace[P.wact] = (m.timestamp, s)

        # lgtBar
        trace[P.lgtBar] = (0.0, False)
        for m in from_table(db, "lightgatetrigger"):
            trace[P.lgtBar] = (m.timestamp, m.broken == 1)

        # rloc
        trace[P.rloc] = (0.0, Loc.inCell)
        trace[P.oloc] = (0.0, None)
        trace[P.otab] = (0.0, False)
        for m in from_table(db, "triggerregionenterevent"):
            if m.entity == "ur10-cobot":
                if m.region == "atWeldSpot":
                    trace[P.rloc] = (m.timestamp, Loc.atWeldSpot)
                if m.region == "sharedTbl":
                    trace[P.rloc] = (m.timestamp, Loc.sharedTbl)
            if m.entity == "Operator-Operator":
                if m.region == "inCell":
                    trace[P.oloc] = (m.timestamp, Loc.inCell)
                if m.region == "atTable":
                    trace[P.otab] = (m.timestamp, True)
        for m in from_table(db, "triggerregionexitevent"):
            if m.entity == "ur10-cobot":
                if m.region == "atWeldSpot":
                    trace[P.rloc] = (m.timestamp, Loc.inCell)
                if m.region == "sharedTbl":
                    trace[P.rloc] = (m.timestamp, Loc.inCell)
            if m.entity == "Operator-Operator":
                if m.region == "inCell":
                    trace[P.oloc] = (m.timestamp, None)
                if m.region == "atTable":
                    trace[P.otab] = (m.timestamp, False)

        # HCp, HSp, HRWp
        trace[P.hcp] = (0.0, Phase.inact)
        trace[P.hsp] = (0.0, Phase.inact)
        trace[P.hrwp] = (0.0, Phase.inact)
        for m in from_table(db, "safetyphasemessage"):
            if m.hazard == "HCp":
                trace[P.hcp] = (m.timestamp, Phase(m.status))
            if m.hazard == "HSp":
                trace[P.hsp] = (m.timestamp, Phase(m.status))
            if m.hazard == "HRWp":
                trace[P.hrwp] = (m.timestamp, Phase(m.status))
            # trace[getattr(P, m.hazard.lower())] = (m.timestamp, Phase(m.status))

        # safmod
        trace[P.safmod] = (0.0, SafMod.normal)
        for m in from_table(db, "safetymoderequest"):
            trace[P.safmod] = (m.timestamp, SafMod(m.status))

        # notif_leaveWrkb
        trace[P.notif_leaveWrkb] = (0.0, False)
        for m in from_table(db, "operatorworkbenchinteraction"):
            trace[P.notif_leaveWrkb] = (m.timestamp, m.status == 1)

        # rngDet
        trace[P.rngDet] = (0.0, RngDet.far)
        for m in from_table(db, "distancemeasurement"):
            if m.distance < 1.0:
                trace[P.rngDet] = (m.timestamp, RngDet.close)
            elif m.distance < 2.0:
                trace[P.rngDet] = (m.timestamp, RngDet.near)
            else:
                trace[P.rngDet] = (m.timestamp, RngDet.far)

        return trace

    def compute_events_combinations(self, trace: Trace):
        """Compute combinations of observed concurrent events"""
        P = SafetyControllerStatus
        # TODO Declare domain with Term definition in monitor
        # TODO Build registry from monitor definition using terms' domain if available
        registry = EventCombinationsRegistry()
        registry.domain[P.notif.id] = Domain({n for n in Notif})
        registry.domain[P.ract.id] = Domain([Act.welding, Act.exchWrkp])
        registry.domain[P.lgtBar.id] = Domain([True, False], True)
        registry.domain[P.rloc.id] = Domain([Loc.inCell, Loc.sharedTbl, Loc.atWeldSpot])
        registry.domain[P.wact.id] = Domain([Act.idle, Act.welding])
        registry.domain[P.safmod.id] = Domain(
            {s for s in SafMod}.difference({SafMod.srmst, SafMod.hguid})
        )
        # .difference( frozenset([SafMod.pflim]) )
        registry.domain[P.notif_leaveWrkb.id] = Domain([True, False])
        registry.domain[P.rngDet.id] = Domain({r for r in RngDet}, True)
        registry.domain[P.hsp.id] = Domain({s for s in Phase}.difference({Phase.mis}))
        registry.domain[P.hcp.id] = Domain({s for s in Phase}.difference({Phase.mis}))
        registry.domain[P.hrwp.id] = Domain({s for s in Phase}.difference({Phase.mis}))
        registry.domain[P.oloc.id] = Domain([Loc.inCell, None], True)
        registry.register(trace)
        #
        with self.event_combinations_output.open("wb") as combinations_file:
            pickle.dump(registry, combinations_file)
        return registry

    def project_events_per_uc(
        self, ucs: Iterable[SafetyUseCase], events: EventCombinationsRegistry
    ):
        """Project events' combinations to individual use case coverage criterion"""
        projection = {}
        for u in ucs:
            projection[u.name] = []
            for i in u.coverage_criterions:
                ci = events.project(i)
                projection[u.name].append((i, ci))
        with self.use_cases_events.open("wb") as uc_events:
            pickle.dump(projection, uc_events)

    def process_output(self):
        """Extract values from simulation message trace"""
        # Process run database
        if not self.database_output.exists():
            raise FileNotFoundError(self.database_output)
        db = DataBase(self.database_output)
        trace = self.build_event_trace(db)
        ucs = self.classify_use_cases(trace)
        combinations = self.compute_events_combinations(trace)
        self.project_events_per_uc(ucs, combinations)

        return trace, self.safety_conditions


if __name__ == "__main__":
    SafetyDigitalTwinRunner.process_output(
        Path("../build/Unity_Data/StreamingAssets/CSI/Databases/messages.safety.db")
    )
