import attr
import itertools
import pickle

from pathlib import Path
from typing import List, Set

from mtl import AtomicPred
from mtl.ast import BinaryOpMTL

from csi.coverage import (
    EventCombinationsRegistry,
    domain_values,
    domain_threshold_range,
)
from csi.monitor import Trace, Monitor
from csi.safety import SafetyCondition, Node
from csi.twin import DigitalTwinRunner, DataBase
from csi.twin.importer import from_table
from scenarios.tcx import unsafe_control_actions

from scenarios.tcx.monitor import World, SafMod, Phase
from scenarios.tcx.safety.hazards import hazards


def load_registry(filename: Path):
    if filename.exists():
        with filename.open("rb") as registry_file:
            return pickle.load(registry_file)
    print(f"Coverage registry '{filename.absolute()}' does not exist")
    return None


def merge_registry(source, target):
    if target is not None:
        source.merge(target)


@attr.s()
class CoverageRecord:
    covered: int = attr.ib()
    total: int = attr.ib()

    @property
    def coverage(self) -> float:
        return float(self.covered) / self.total


class CoverageReport:
    atom_coverage: dict[int, CoverageRecord]
    condition_coverage: dict[int, CoverageRecord]
    predicate_coverage: dict[int, CoverageRecord]
    safety_coverage: dict[int, CoverageRecord]

    def __init__(self):
        self.atom_coverage = dict()
        self.condition_coverage = dict()
        self.predicate_coverage = dict()
        self.safety_coverage = dict()


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
        "atWeldSpot": "in_tool",
        # "atTable": "in_bench",
        "sharedTbl": "in_bench",
        "inCell": "in_workspace",
    }

    all_safety_conditions: List[SafetyCondition] = list(unsafe_control_actions) + list(
        hazards
    )

    @property
    def safety_conditions(self):
        return list(
            s for s in self.all_safety_conditions if s.uid not in self.blacklist
        )

    blacklist: Set[str] = {"UCA9-N-1", "7"}

    event_combinations_output: Path = Path("events_combinations.pkl")

    coverage_root: Path = Path("coverage")
    coverage_combinations: int = 2

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
        P = World
        # TODO Declare domain with Term definition in monitor
        registry = EventCombinationsRegistry()
        # registry.domain[P.notif.id] = Domain({n for n in Notif})
        # registry.domain[P.constraints.cobot.distance.proximity] = Domain( { None, } )
        # registry.domain[P.constraints.cobot.velocity.proximity] = Domain({None,})
        # registry.domain[P.constraints.cobot.velocity.in_bench] = Domain({None,})
        # registry.domain[P.constraints.tool.distance.operation] = Domain( { None, } )
        # registry.domain[P.constraints.cobot.velocity.in_tool] =
        # registry.domain[P.constraints.cobot.velocity.in_workspace] =
        registry.domain[P.safety.mode] = domain_values(list(SafMod))
        registry.domain[P.safety.hrwp] = domain_values(list(Phase))
        registry.domain[P.safety.hcp] = domain_values(list(Phase))
        registry.domain[P.safety.hsp] = domain_values(list(Phase))
        registry.domain[P.tool.distance] = domain_threshold_range(
            0.0, 4.0, 0.25, upper=True
        )
        registry.domain[P.cobot.distance] = domain_threshold_range(
            0.0, 4.0, 0.25, upper=True
        )
        registry.domain[P.cobot.velocity] = domain_threshold_range(
            0.0, 16.0, 0.25, upper=True
        )
        registry.domain[P.cobot.position.in_workspace] = domain_values({True, False})
        registry.domain[P.assembly.position.in_bench] = domain_values({True, False})
        registry.domain[P.assembly.is_damaged] = domain_values({True, False})
        registry.domain[P.cobot.reaches_target] = domain_values({True, False})
        registry.domain[P.operator.is_damaged] = domain_values({True, False})
        registry.domain[P.cobot.is_damaged] = domain_values({True, False})
        registry.domain[P.operator.position.in_bench] = domain_values({True, False})
        registry.domain[P.tool.is_damaged] = domain_values({True, False})
        registry.domain[P.tool.is_running] = domain_values({True, False})
        registry.domain[P.cobot.has_target] = domain_values({True, False})
        registry.domain[P.assembly.is_secured] = domain_values({True, False})
        registry.domain[P.assembly.is_processed] = domain_values({True, False})
        registry.domain[P.controller.is_configured] = domain_values({True, False})
        registry.domain[P.operator.provides_assembly] = domain_values({True, False})
        registry.domain[P.assembly.is_orientation_valid] = domain_values({True, False})
        registry.domain[P.cobot.has_assembly] = domain_values({True, False})
        registry.domain[P.cobot.position.in_bench] = domain_values({True, False})
        registry.domain[P.assembly.is_moving] = domain_values({True, False})
        registry.domain[P.cobot.is_moving] = domain_values({True, False})
        registry.domain[P.assembly.under_processing] = domain_values({True, False})
        registry.domain[P.assembly.is_valid] = domain_values({True, False})
        registry.domain[P.operator.position.in_workspace] = domain_values({True, False})
        registry.domain[P.cobot.position.in_tool] = domain_values({True, False})
        registry.domain[P.operator.has_assembly] = domain_values({True, False})
        registry.domain[P.lidar.is_damaged] = domain_values({True, False})
        registry.domain[P.tool.has_assembly] = domain_values({True, False})
        return registry

    @staticmethod
    def extract_boolean_predicates(safety_conditions) -> Set[Node]:
        terms: Set[AtomicPred] = set()
        comparisons: Set[BinaryOpMTL] = set()
        # Extract all candidates
        for s in safety_conditions:
            local_comparisons = set()
            for p in s.condition.walk():
                if isinstance(p, AtomicPred):
                    terms.add(p)
                if isinstance(p, BinaryOpMTL):
                    local_comparisons.add(p)
            for p in list(local_comparisons):
                if any(
                    c.children == p.children and p.OP == "=" and c.OP == "<"
                    for c in local_comparisons
                ):
                    local_comparisons.remove(p)
            comparisons.update(local_comparisons)
        # Remove values used in comparisons
        for p in comparisons:
            terms = terms.difference(p.children)
        return set(itertools.chain(terms, comparisons))

    def process_output(self):
        """Extract values from simulation message trace"""
        # Process run database
        if not self.database_output.exists():
            raise FileNotFoundError(self.database_output)
        db = DataBase(self.database_output)
        trace = self.build_event_trace(db)
        return trace, self.safety_conditions
