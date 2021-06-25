import json
import pickle

from pathlib import Path
from typing import List, Iterable

from csi.coverage import EventCombinationsRegistry, Domain
from csi.monitor import Trace, Monitor
from csi.safety import SafetyCondition
from csi.twin import DigitalTwinRunner, DataBase
from csi.twin.importer import from_table
from scenarios.tcx import unsafe_control_actions

from scenarios.tcx.monitor import World
from scenarios.tcx.safety.hazards import hazards


class SafecompControllerRunner(DigitalTwinRunner):
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
    }

    safety_conditions: List[SafetyCondition] = list(unsafe_control_actions) + list(
        hazards
    )

    event_combinations_output: Path = Path("events_combinations.pkl")

    def build_event_trace(self, db: DataBase) -> Trace:
        """Extract event stream from run message stream"""
        # Prepare trace
        trace = Trace()
        P = World()

        # Entity.distance
        for m in from_table(db, "distancemeasurement"):
            trace[self.entity[m.entity].distance] = (m.timestamp, m.distance)

        # Entity.velocity
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
        for m in from_table(db, "movablestatus"):
            trace[self.entity[m.entity].is_moving] = (m.timestamp, bool(m.is_moving))

        for m in from_table(db, "actstatus"):
            if m.topic == "welder/mode/update":
                if m.status == 1:
                    trace[P.tool.is_running] = (m.timestamp, False)
                elif m.status == 0:
                    trace[P.tool.is_running] = (m.timestamp, True)
                else:
                    raise Exception("Unknown welder status")

        # Define constraints
        trace[P.constraints.cobot.velocity.in_bench] = (0.0, 1.5)
        trace[P.constraints.cobot.velocity.in_tool] = (0.0, 1.5)
        trace[P.constraints.cobot.velocity.in_workspace] = (0.0, 2.5)
        trace[P.constraints.cobot.velocity.proximity] = (0.0, 0.75)
        trace[P.constraints.cobot.distance.proximity] = (0.0, 0.5)
        trace[P.constraints.tool.distance.operation] = (0.0, 0.5)

        # FIXME Remove temporary values
        #        trace[P.assembly.has_assembly] = (0.0, False)
        #        trace[P.assembly.is_orientation_valid] = (0.0, True)
        #        trace[P.assembly.is_processed] = (0.0, True)
        #        trace[P.assembly.is_secured] = (0.0, True)
        #        trace[P.assembly.is_valid] = (0.0, True)
        #        trace[P.assembly.under_processing] = (0.0, False)
        #        trace[P.cobot.has_assembly] = (0.0, False)
        #        trace[P.controller.is_configured] = (0.0, True)
        #        trace[P.operator.has_assembly] = (0.0, False)
        #        trace[P.operator.provides_assembly] = (0.0, False)
        #        trace[P.tool.has_assembly] = (0.0, False)
        #        trace[P.tool.is_running] = (0.0, False)

        return trace

    def compute_events_combinations(self, trace: Trace):
        """Compute combinations of observed concurrent events"""
        P = World
        # TODO Declare domain with Term definition in monitor
        # TODO Accept values even out of domain and add method to restrict record to domain afterwards
        # TODO Add support for continuous domains
        registry = EventCombinationsRegistry()
        # registry.domain[P.notif.id] = Domain({n for n in Notif})
        # registry.domain[P.constraints.cobot.distance.proximity] = Domain( { None, } )
        # registry.domain[P.constraints.cobot.velocity.proximity] = Domain({None,})
        # registry.domain[P.constraints.cobot.velocity.in_bench] = Domain({None,})
        # registry.domain[tool.distance] = Domain({None, })
        # registry.domain[P.constraints.cobot.velocity.in_tool] = Domain( { None, } )
        # registry.domain[P.constraints.tool.distance.operation] = Domain( { None, } )
        # registry.domain[P.constraints.cobot.velocity.in_workspace] = Domain( { None, } )
        # registry.domain[P.cobot.distance] = Domain( { None, } )
        # registry.domain[P.cobot.velocity] = Domain({ None, } )
        registry.domain[P.cobot.position.in_workspace] = Domain({True, False})
        registry.domain[P.assembly.position.in_bench] = Domain({True, False})
        registry.domain[P.assembly.is_damaged] = Domain({True, False})
        registry.domain[P.cobot.reaches_target] = Domain({True, False})
        registry.domain[P.operator.is_damaged] = Domain({True, False})
        registry.domain[P.cobot.is_damaged] = Domain({True, False})
        registry.domain[P.operator.position.in_bench] = Domain({True, False})
        registry.domain[P.tool.is_damaged] = Domain({True, False})
        registry.domain[P.tool.is_running] = Domain({True, False})
        registry.domain[P.cobot.has_target] = Domain({True, False})
        registry.domain[P.assembly.is_secured] = Domain({True, False})
        registry.domain[P.assembly.is_processed] = Domain({True, False})
        registry.domain[P.controller.is_configured] = Domain({True, False})
        registry.domain[P.operator.provides_assembly] = Domain({True, False})
        registry.domain[P.assembly.is_orientation_valid] = Domain({True, False})
        registry.domain[P.cobot.has_assembly] = Domain({True, False})
        registry.domain[P.cobot.position.in_bench] = Domain({True, False})
        registry.domain[P.lidar.has_assembly] = Domain({True, False})
        registry.domain[P.assembly.is_moving] = Domain({True, False})
        registry.domain[P.cobot.is_moving] = Domain({True, False})
        registry.domain[P.assembly.under_processing] = Domain({True, False})
        registry.domain[P.assembly.is_valid] = Domain({True, False})
        registry.domain[P.operator.position.in_workspace] = Domain({True, False})
        registry.domain[P.assembly.has_assembly] = Domain({True, False})
        registry.domain[P.cobot.position.in_tool] = Domain({True, False})
        registry.domain[P.operator.has_assembly] = Domain({True, False})
        registry.domain[P.lidar.is_damaged] = Domain({True, False})
        registry.domain[P.tool.has_assembly] = Domain({True, False})
        #
        with self.event_combinations_output.open("wb") as combinations_file:
            pickle.dump(registry, combinations_file)
        return registry

    def process_output(self):
        """Extract values from simulation message trace"""
        # Process run database
        if not self.database_output.exists():
            raise FileNotFoundError(self.database_output)
        db = DataBase(self.database_output)
        trace = self.build_event_trace(db)
        # Check for missing atoms
        monitor = Monitor()
        for s in self.safety_conditions:
            monitor += s.condition
        missing_atoms = sorted(a for a in monitor.atoms() - trace.atoms())
        # Compute events combinations
        combinations = self.compute_events_combinations(trace)

        return trace, self.safety_conditions


if __name__ == "__main__":
    SafecompControllerRunner.process_output(
        Path("../build/Unity_Data/StreamingAssets/CSI/Databases/messages.safety.db")
    )
