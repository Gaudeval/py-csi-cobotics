import dataclasses
import math
from pathlib import Path
from typing import Any, Mapping

from csi.monitor import Trace, Monitor
from csi.twin.importer import as_object
from csi.twin import BuildRunnerConfiguration, BuildRunner, DataBase
from scenarios.tcx import WorldData, P


@dataclasses.dataclass
class TcxRunnerConfiguration(BuildRunnerConfiguration):
    """Digital twin experiment configuration"""

    world: Any = dataclasses.field(default_factory=WorldData)
    build: Path = dataclasses.field(default_factory=Path)


def safety_timestamp(row: Mapping):
    v = next(iter(row.values()))
    if "timestamp" in v:
        return int(math.floor(v.get("timestamp") * 1000))
    return None


class TcxBuildRunner(BuildRunner):
    entity = {
        "ur10-cobot": P.cobot,
        "Tim-Operator": P.operator,
        "TT7302-mandrel-assembly": P.assembly,
        "Spot Welder Assembly-welder": P.tool,
    }

    region = {
        "Work Cell Region": "in_workspace",
        "Loading Platform Region": "in_bench",
        "Spot Welder Region": "in_tool",
    }

    def process_output(self, database_path, safety_conditions=None):
        """Extract values from simulation message trace"""
        # Define safety monitor
        monitor = Monitor()
        for safety_condition in safety_conditions:
            monitor += safety_condition.condition
        # Import trace
        db = DataBase(database_path)
        trace = Trace()

        def from_table(*table):
            return map(as_object, db.flatten_messages(*table))

        # tables = set(db.tables.keys())

        # Entity.distance
        for m in from_table("distancemeasurement"):
            trace[self.entity[m.entity].distance] = (m.timestamp, m.distance)

        # Entity.velocity
        for m in from_table("velocitymeasurement"):
            trace[self.entity[m.entity].velocity] = (m.timestamp, m.velocity)

        # Entity.reaches_target
        for m in from_table("waypointnotification"):
            if m.achiever == "ur10":
                trace[P.cobot.reaches_target] = (m.timestamp, True)
                trace[P.cobot.has_target] = (m.timestamp, False)
                trace[P.cobot.reaches_target] = (m.timestamp + 0.1, False)

        # Entity.has_target
        for m in from_table("waypointrequest"):
            trace[P.cobot.has_target] = (m.timestamp, True)

        # Entity.is_damaged
        for m in from_table("damageablestatus"):
            trace[self.entity[m.entity].is_damaged] = (m.timestamp, bool(m.is_damaged))

        # Entity.position
        # Initialise all position all entities to False
        for e in self.entity.values():
            for p in self.region.values():
                trace[getattr(e.position, p)] = (0.0, False)
        # Collect position from message
        for m in from_table("triggerregionenterevent", "triggerregionexitevent"):
            v = "enter" in m.__table__
            p = getattr(self.entity[m.entity].position, self.region[m.region])
            trace[p] = (m.timestamp, v)

        # Entity.is_moving
        for m in from_table("movablestatus"):
            trace[self.entity[m.entity].is_moving] = (m.timestamp, bool(m.is_moving))

        # Define constraints
        trace[P.constraints.cobot.velocity.in_bench] = (0.0, 1.5)
        trace[P.constraints.cobot.velocity.in_tool] = (0.0, 1.5)
        trace[P.constraints.cobot.velocity.in_workspace] = (0.0, 2.5)
        trace[P.constraints.cobot.velocity.proximity] = (0.0, 0.75)
        trace[P.constraints.cobot.distance.proximity] = (0.0, 0.5)
        trace[P.constraints.tool.distance.operation] = (0.0, 0.5)

        missing_atoms = sorted(a.id for a in monitor.atoms() - trace.atoms())

        # FIXME Remove temporary values
        trace[P.assembly.has_assembly] = (0.0, False)
        trace[P.assembly.is_orientation_valid] = (0.0, True)
        trace[P.assembly.is_processed] = (0.0, True)
        trace[P.assembly.is_secured] = (0.0, True)
        trace[P.assembly.is_valid] = (0.0, True)
        trace[P.assembly.under_processing] = (0.0, False)
        trace[P.cobot.has_assembly] = (0.0, False)
        trace[P.controller.is_configured] = (0.0, True)
        trace[P.operator.has_assembly] = (0.0, False)
        trace[P.operator.provides_assembly] = (0.0, False)
        trace[P.tool.has_assembly] = (0.0, False)
        trace[P.tool.is_running] = (0.0, False)

        return trace, safety_conditions
