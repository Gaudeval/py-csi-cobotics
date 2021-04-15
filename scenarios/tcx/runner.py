import dataclasses
import math
from pathlib import Path
from typing import Any, Mapping

from csi.monitor import Trace, Monitor
from csi.twin.importer import as_object
from csi.twin import DigitalTwinConfiguration, DigitalTwinRunner, DataBase
from scenarios.tcx import WorldData, P


@dataclasses.dataclass
class TcxConfiguration(DigitalTwinConfiguration):
    """Digital twin experiment configuration"""

    world: Any = dataclasses.field(default_factory=WorldData)
    build: Path = dataclasses.field(default_factory=Path)


def safety_timestamp(row: Mapping):
    v = next(iter(row.values()))
    if "timestamp" in v:
        return int(math.floor(v.get("timestamp") * 1000))
    return None


# TODO Restore saving screenshots
class TcxDigitalTwinRunner(DigitalTwinRunner):
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

    @classmethod
    def process_output(cls, database_path, safety_conditions=None):
        """Extract values from simulation message trace"""
        # Define safety monitor
        monitor = Monitor()
        for safety_condition in safety_conditions:
            monitor += safety_condition.condition
        # Import trace
        if not Path(database_path).exists():
            raise FileNotFoundError(database_path)
        db = DataBase(database_path)
        trace = Trace()

        def from_table(*table):
            return map(as_object, db.flatten_messages(*table))

        # tables = set(db.tables.keys())

        # Entity.distance
        for m in from_table("distancemeasurement"):
            trace[cls.entity[m.entity].distance] = (m.timestamp, m.distance)

        # Entity.velocity
        for m in from_table("velocitymeasurement"):
            trace[cls.entity[m.entity].velocity] = (m.timestamp, m.velocity)

        # Entity.reaches_target
        trace[P.cobot.reaches_target] = (0.0, False)
        for m in from_table("waypointnotification"):
            if m.achiever == "ur10" and m.label == "waypoint/progress":
                trace[P.cobot.reaches_target] = (m.timestamp, True)
                trace[P.cobot.has_target] = (m.timestamp, False)
                trace[P.cobot.reaches_target] = (m.timestamp + 0.1, False)

        # Entity.has_target
        for m in from_table("waypointrequest"):
            trace[P.cobot.has_target] = (m.timestamp, True)

        # Entity.is_damaged
        trace[P.assembly.is_damaged] = (0.0, False)
        trace[P.tool.is_damaged] = (0.0, False)
        trace[P.operator.is_damaged] = (0.0, False)
        trace[P.cobot.is_damaged] = (0.0, False)
        for m in from_table("damageablestatus"):
            trace[cls.entity[m.entity].is_damaged] = (m.timestamp, bool(m.is_damaged))

        # Entity.position
        # Initialise all position all entities to False
        for e in cls.entity.values():
            for p in cls.region.values():
                trace[getattr(e.position, p)] = (0.0, False)
        # Collect position from message
        for m in from_table("triggerregionenterevent", "triggerregionexitevent"):
            if m.region not in cls.region or m.entity not in cls.entity:
                continue
            v = "enter" in m.__table__
            p = getattr(cls.entity[m.entity].position, cls.region[m.region])
            trace[p] = (m.timestamp, v)

        # Entity.is_moving
        for m in from_table("movablestatus"):
            trace[cls.entity[m.entity].is_moving] = (m.timestamp, bool(m.is_moving))

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
