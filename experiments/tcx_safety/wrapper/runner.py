import itertools
import pickle
import shutil
import tempfile

from pathlib import Path
from typing import List, Set

import docker
from mtfl import AtomicPred
from mtfl.ast import BinaryOpMTL

from csi.configuration import ConfigurationManager
from csi.situation.coverage import EventCombinationsRegistry
from csi.situation.domain import domain_values, domain_threshold_range
from csi.experiment import Experiment
from csi.situation.monitoring import Monitor, Trace
from csi.safety import SafetyCondition
from csi.situation.components import Node
from csi.twin import DataBase
from csi.twin.importer import from_table

from .monitor import World, SafMod, Phase
from .safety import hazards, unsafe_control_actions


class SafecompControllerRunner(Experiment):
    image_name: str = "csi-twin:tcx"

    # Collected or generated run files
    configuration_output = Path("assets/configuration.json")
    database_output = Path("assets/database.sqlite")
    trace_output: Path = Path("events_trace.pkl")

    entity = {
        "ur10-cobot": World.cobot,
        "Operator-Operator": World.operator,
        "TT7302-mandrel-assembly": World.assembly,
        "SpotWelder-welder": World.tool,
        "469ef06d-0045-4ce7-9dd4-513eef7aedb6": World.lidar,
    }

    region = {
        "Work Cell Region": "in_workspace",
        "Loading Platform Region": "in_bench",
        "Spot Welder Region": "in_tool",
        "atWeldSpot": "in_tool",
        # "atTable": "in_bench",
        "sharedTbl": "in_bench",
        "inCell": "in_workspace",
    }

    @property
    def safety_conditions(self):
        return list(
            s
            for s in list(unsafe_control_actions) + list(hazards)
            if s.uid not in self.blacklist
        )

    blacklist: Set[str] = {"UCA9-N-1", "7"}

    def execute(self) -> None:
        """Run digital twin container with the specified configuration"""
        with tempfile.TemporaryDirectory() as configuration_root, tempfile.TemporaryDirectory() as database_root:
            # Setup configuration
            configuration_dir = Path(configuration_root)
            configuration_file = self.configuration.build.configuration.name
            configuration_path = configuration_dir / configuration_file
            ConfigurationManager().save(self.configuration.world, configuration_path)
            # Setup database output
            database_dir = Path(database_root)
            database_file = self.configuration.build.database.name
            database_path = database_dir / database_file
            # Run twin container
            try:
                client = docker.from_env()
                logs = client.containers.run(
                    self.image_name,
                    auto_remove=True,
                    volumes={
                        str(configuration_dir.absolute()): {
                            "bind": "/csi/configuration",
                            "mode": "rw",
                        },
                        str(database_dir.absolute()): {
                            "bind": "/csi/databases",
                            "mode": "rw",
                        },
                    },
                    stdout=True,
                    stderr=True,
                )
                print(logs)
            finally:
                self.collect_output(configuration_path, database_path)
        # Check for hazard occurrence
        trace, conditions = self.process_output()
        self.produce_safety_report(trace, conditions)
        # Backup processed trace
        with self.trace_output.open("wb") as trace_file:
            pickle.dump(trace, trace_file)

    def collect_output(self, configuration_path, database_path):
        """Collect generated files in run folder"""
        self.database_output.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(database_path, self.database_output)
        self.configuration_output.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(configuration_path, self.configuration_output)

    def build_event_trace(self, db: DataBase) -> Trace:
        """Extract event stream from run message stream"""
        # Prepare trace
        trace = Trace()
        P = World()

        # safety.mode
        trace[P.safety.mode] = (0.0, SafMod.NORMAL)
        for m in from_table(db, "safetymoderequest"):
            trace[P.safety.mode] = (m.timestamp, SafMod(m.status))

        # safety.hazards
        trace[P.safety.hcp] = (0.0, Phase.INACT)
        trace[P.safety.hsp] = (0.0, Phase.INACT)
        trace[P.safety.hrwp] = (0.0, Phase.INACT)
        for m in from_table(db, "safetyphasemessage"):
            if m.hazard == "HCp":
                trace[P.safety.hcp] = (m.timestamp, Phase(m.status))
            if m.hazard == "HSp":
                trace[P.safety.hsp] = (m.timestamp, Phase(m.status))
            if m.hazard == "HRWp":
                trace[P.safety.hrwp] = (m.timestamp, Phase(m.status))

        # Entity.distance
        trace[P.cobot.distance] = (0.0, float("inf"))
        trace[P.tool.distance] = (0.0, float("inf"))
        for m in from_table(db, "float32"):
            if m.topic == "welder/operator_distance":
                trace[P.tool.distance] = (m.timestamp, m.data)
            if m.topic == "cobot/operator_distance":
                trace[P.cobot.distance] = (m.timestamp, m.data)

        # Entity.velocity
        trace[P.cobot.velocity] = (0.0, 0.0)
        for m in from_table(db, "velocitymeasurement"):
            trace[self.entity[m.entity].velocity] = (m.timestamp, m.velocity)

        # Entity.reaches_target
        trace[P.cobot.reaches_target] = (0.0, False)
        for m in from_table(db, "waypointnotification"):
            if m.achiever == "ur10" and m.label == "waypoint/progress":
                trace[P.cobot.reaches_target] = (m.timestamp, True)
                trace[P.cobot.has_target] = (m.timestamp, False)
                trace[P.cobot.reaches_target] = (m.timestamp + 0.1, False)

        # Entity.has_target
        for m in from_table(db, "waypointrequest"):
            trace[P.cobot.has_target] = (m.timestamp, True)

        # Entity.is_damaged
        trace[P.assembly.is_damaged] = (0.0, False)
        trace[P.tool.is_damaged] = (0.0, False)
        trace[P.operator.is_damaged] = (0.0, False)
        trace[P.cobot.is_damaged] = (0.0, False)
        for m in from_table(db, "damageablestatus"):
            trace[self.entity[m.entity].is_damaged] = (m.timestamp, bool(m.is_damaged))

        # Entity.position
        # Initialise all position all entities to False
        for e in self.entity.values():
            for p in self.region.values():
                trace[getattr(e.position, p)] = (0.0, False)
        # Collect position from message
        for m in from_table(db, "triggerregionenterevent", "triggerregionexitevent"):
            if m.region not in self.region or m.entity not in self.entity:
                continue
            v = "enter" in m.__table__
            p = getattr(self.entity[m.entity].position, self.region[m.region])
            trace[p] = (m.timestamp, v)

        # Entity.is_moving
        for e in self.entity.values():
            trace[e.is_moving] = (0.0, False)
        for m in from_table(db, "movablestatus"):
            trace[self.entity[m.entity].is_moving] = (m.timestamp, bool(m.is_moving))

        welder_running = False
        trace[P.tool.has_assembly] = (0.0, False)
        trace[P.cobot.has_assembly] = (0.0, True)
        trace[P.operator.has_assembly] = (0.0, False)
        trace[P.tool.is_running] = (0.0, False)
        trace[P.assembly.under_processing] = (0.0, False)
        trace[P.assembly.is_processed] = (0.0, False)
        for m in from_table(db, "entitystatus"):
            if m.topic.startswith("welder"):
                # 0 Unknown
                # 2 Active
                # 7 Idle
                # 10 Waiting
                # 7 -> 10 -> 2 -> 7
                # Capture assembly processed status
                if m.status in [2, 10]:
                    if welder_running:
                        trace[P.assembly.is_processed] = (m.timestamp, True)
                    welder_running = False
                elif m.status in [7]:
                    welder_running = True
                elif m.status in [0]:
                    welder_running = False
                #
                if m.status == 2:
                    trace[P.tool.is_running] = (m.timestamp, True)
                    trace[P.tool.has_assembly] = (m.timestamp, True)
                    trace[P.assembly.under_processing] = (m.timestamp, True)
                elif m.status == 10:
                    trace[P.tool.is_running] = (m.timestamp, False)
                    trace[P.tool.has_assembly] = (m.timestamp, True)
                    trace[P.assembly.under_processing] = (m.timestamp, False)
                elif m.status == 7:
                    trace[P.tool.is_running] = (m.timestamp, False)
                    trace[P.tool.has_assembly] = (m.timestamp, False)
                    trace[P.assembly.under_processing] = (m.timestamp, False)
                elif m.status == 0:
                    trace[P.tool.is_running] = (m.timestamp, False)
                    trace[P.tool.has_assembly] = (m.timestamp, False)
                    trace[P.assembly.under_processing] = (m.timestamp, False)
                else:
                    raise Exception("Unknown welder status")

        # Placeholder for know values/constants
        trace[P.controller.is_configured] = (0.0, True)
        trace[P.lidar.is_damaged] = (0.0, False)

        # Placeholder for non-modelled properties
        trace[P.assembly.is_orientation_valid] = (0.0, True)
        trace[P.assembly.is_secured] = (0.0, True)
        trace[P.assembly.is_valid] = (0.0, True)
        trace[P.operator.provides_assembly] = (0.0, False)

        # Define constraints
        trace[P.constraints.cobot.velocity.in_bench] = (0.0, 15.0)
        trace[P.constraints.cobot.velocity.in_tool] = (0.0, 15.0)
        trace[P.constraints.cobot.velocity.in_workspace] = (0.0, 100.0)
        trace[P.constraints.cobot.velocity.proximity] = (0.0, 9.0)
        trace[P.constraints.cobot.distance.proximity] = (0.0, 0.5)
        trace[P.constraints.tool.distance.operation] = (0.0, 0.5)

        return trace

    def initialise_registry(self) -> EventCombinationsRegistry:
        """Define event domain for use case."""
        P = World
        registry = EventCombinationsRegistry()
        # TODO List all domains and register them from World
        # TODO Remove method... kind of unused
        return registry

    def process_output(self):
        """Extract values from simulation message trace"""
        # Process run database
        if not self.database_output.exists():
            raise FileNotFoundError(self.database_output)
        db = DataBase(self.database_output)
        trace = self.build_event_trace(db)
        return trace, self.safety_conditions

    def produce_safety_report(self, trace, conditions):
        """Compute the occurrence of the conditions on the provided trace"""
        report = {}
        monitor = Monitor(c.condition for c in conditions)
        r = monitor.evaluate(
            trace,
            dt=0.01,
            quantitative=self.configuration.ltl.quantitative,
            logic=self.configuration.ltl.logic,
        )
        for c in conditions:
            report[c.uid] = r[c.condition]
        with open("./hazard-report.json", "w") as json_report:
            import json
            json.dump(report, json_report, indent=4)
        return report
