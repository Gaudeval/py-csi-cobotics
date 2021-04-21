import json
import pickle

from pathlib import Path
from typing import List, Iterable

from csi.coverage import EventCombinationsRegistry
from csi.monitor import Trace
from csi.safety import SafetyCondition
from csi.twin import DigitalTwinRunner, DataBase
from csi.twin.importer import from_table

from .monitor import SafetyControllerStatus, Notif, Act, Loc, RngDet, SafMod, Phase
from .uc import SafetyUseCase, U1, U2, MU
from .validation import predicates


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
            raise NotImplementedError

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
        registry.domain[P.notif.id] = frozenset(n for n in Notif)
        registry.domain[P.ract.id] = frozenset([Act.welding, Act.exchWrkp])
        registry.domain[P.lgtBar.id] = frozenset([True, False])
        registry.domain[P.rloc.id] = frozenset(
            [Loc.inCell, Loc.sharedTbl, Loc.atWeldSpot]
        )
        registry.domain[P.wact.id] = frozenset([Act.idle, Act.welding])
        registry.domain[P.safmod.id] = frozenset(s for s in SafMod)
        registry.domain[P.notif_leaveWrkb.id] = frozenset([True, False])
        registry.domain[P.rngDet.id] = frozenset(r for r in RngDet)
        registry.domain[P.hsp.id] = frozenset(s for s in Phase)
        registry.domain[P.hcp.id] = frozenset(s for s in Phase)
        registry.domain[P.hrwp.id] = frozenset(s for s in Phase)
        registry.domain[P.oloc.id] = frozenset([Loc.inCell, None])
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
