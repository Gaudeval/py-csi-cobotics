import attr
import collections
import hashlib
import itertools
import json
import pickle
from tqdm import tqdm

from multiprocessing import Pool
from pathlib import Path
from typing import List, Iterable, Set

from mtl import AtomicPred
from mtl.ast import BinaryOpMTL

from csi.coverage import (
    EventCombinationsRegistry,
    domain_values,
    domain_threshold_range,
    domain_identity,
)
from csi.monitor import Trace, Monitor
from csi.safety import SafetyCondition, Node
from csi.twin import DigitalTwinRunner, DataBase
from csi.twin.importer import from_table
from scenarios.tcx import unsafe_control_actions

from scenarios.tcx.monitor import World, SafMod, Phase
from scenarios.tcx.safety.hazards import hazards

from .utils import as_working_directory


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
        for m in from_table(db, "distancemeasurement"):
            trace[self.entity[m.entity].distance] = (m.timestamp, m.distance)

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

    def compute_events_combinations(self, trace: Trace):
        """Compute combinations of observed concurrent events"""
        #
        # TODO Restrict domains for atom coverage
        registry = self.initialise_registry()
        registry = registry.restrict({k: domain_identity() for k in registry.domain})
        registry.register(trace)
        with self.event_combinations_output.open("wb") as combinations_file:
            pickle.dump(
                registry.restrict(self.initialise_registry().domain), combinations_file
            )
        return registry

    def compute_coverage(self, trace, monitor, registry):
        # Obtain safety report
        self.produce_safety_report(trace, self.safety_conditions, quiet=True)
        with open("./hazard-report.json", "r") as json_report:
            report = json.load(json_report)
        # Compute atom coverage
        atoms = set(monitor.atoms()) & set(registry.domain.keys())
        self.compute_atom_coverage(atoms, registry)
        # Compute safety and condition coverage
        self.compute_condition_coverage(report)
        # Compute predicate coverage
        self.compute_predicate_coverage(trace)

    def compute_atom_coverage(self, atoms, registry):
        # Compute all combinations of atom values as per domain
        atom_registry = registry.restrict(self.initialise_registry().domain)
        atom_registry = atom_registry.project(atoms)
        # Save combinations of atom values
        atom_path = self.coverage_root / "atom" / f"registry.pkl"
        atom_path.parent.mkdir(parents=True, exist_ok=True)
        with atom_path.open("wb") as atom_file:
            pickle.dump(atom_registry, atom_file)
        # Compute atom values per combinations of atoms
        for n in range(1, self.coverage_combinations + 1):
            for atom_group in itertools.combinations(atoms, n):
                group_name = "-".join(
                    ".".join(a.id) for a in sorted(atom_group, key=lambda a: a.id)
                )
                group_path = atom_path.parent / str(n) / f"registry-{group_name}.pkl"
                group_path.parent.mkdir(parents=True, exist_ok=True)
                with group_path.open("wb") as group_file:
                    pickle.dump(atom_registry.project(list(atom_group)), group_file)

    def compute_condition_coverage(self, report):
        # Compute domain for condition coverage
        uids = []
        condition_registry = EventCombinationsRegistry()
        for condition in self.safety_conditions:
            uids.append(condition.uid)
            condition_registry.domain[condition.uid] = domain_values({True, False})
        # Compute and record condition coverage metrics
        condition_registry.record(
            {u: True if float(report.get(u, False)) >= 1.0 else False for u in uids}
        )
        condition_path = self.coverage_root / "condition" / f"registry.pkl"
        condition_path.parent.mkdir(parents=True, exist_ok=True)
        with condition_path.open("wb") as condition_file:
            pickle.dump(condition_registry, condition_file)
        # Compute and record safety coverage metrics
        safety_domain = {u: domain_values({True}) for u in uids}
        safety_path = self.coverage_root / "safety" / f"registry.pkl"
        safety_path.parent.mkdir(parents=True, exist_ok=True)
        with safety_path.open("wb") as safety_file:
            pickle.dump(condition_registry.restrict(safety_domain), safety_file)
        # Compute condition/safety metrics per combinations of condition
        for n in range(1, self.coverage_combinations + 1):
            for condition_group in itertools.combinations(uids, n):
                group_name = "_".join(sorted(condition_group))
                group_registry = condition_registry.project(list(condition_group))
                # Record condition metric
                group_path = (
                    condition_path.parent / str(n) / f"registry-{group_name}.pkl"
                )
                group_path.parent.mkdir(parents=True, exist_ok=True)
                with group_path.open("wb") as group_file:
                    pickle.dump(group_registry, group_file)
                # Record safety metric
                group_path = safety_path.parent / str(n) / f"registry-{group_name}.pkl"
                group_path.parent.mkdir(parents=True, exist_ok=True)
                with group_path.open("wb") as group_file:
                    pickle.dump(group_registry.restrict(safety_domain), group_file)

    def compute_predicate_coverage(self, trace):
        predicates = self.extract_boolean_predicates(self.safety_conditions)
        # Prepare registry domain for boolean predicates
        predicate_registry = self.initialise_registry()
        predicate_registry = predicate_registry.project(predicates)
        # Evaluate boolean predicate values over time
        for p in predicates:
            if not isinstance(p, AtomicPred):
                predicate_valuation = Monitor().evaluate(
                    trace,
                    p,
                    dt=0.01,
                    quantitative=self.configuration.ltl.quantitative,
                    logic=self.configuration.ltl.logic,
                    time=None,
                )
                for time, value in predicate_valuation:
                    trace[p] = (time, value)
                predicate_registry.domain[p] = domain_values({True, False})
        # Compute and record coverage over all predicate combinations
        predicate_registry.register(trace)
        predicate_path = self.coverage_root / "predicate" / f"registry.pkl"
        predicate_path.parent.mkdir(parents=True, exist_ok=True)
        with predicate_path.open("wb") as safety_file:
            pickle.dump(predicate_registry, safety_file)
        # Compute coverage metrics per combinations of predicates
        for n in range(1, self.coverage_combinations + 1):
            for predicate_group in itertools.combinations(predicates, n):
                #
                group = []
                for p in predicate_group:
                    if isinstance(p, AtomicPred):
                        group.append(".".join(p.id))
                    else:
                        group.append(hashlib.md5(str(p).encode()).hexdigest())
                #
                group_name = "_".join(sorted(group))
                group_registry = predicate_registry.project(list(predicate_group))
                # Record condition metric
                group_path = (
                    predicate_path.parent / str(n) / f"registry-{group_name}.pkl"
                )
                group_path.parent.mkdir(parents=True, exist_ok=True)
                with group_path.open("wb") as group_file:
                    pickle.dump(group_registry, group_file)

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

    @staticmethod
    def merge_coverage(repository) -> CoverageReport:
        # Merge coverage metrics
        runs = {(e, r) for (e, r) in repository.completed_runs}
        coverage_files = set()
        #
        for e, r in tqdm(runs, desc="Collecting coverage record names"):
            e: SafecompControllerRunner
            runs.add((e, r))
            with as_working_directory(r.work_path):
                coverage_files.update(e.coverage_root.glob("**/registry-*.pkl"))
        #
        registries = dict()
        for e, r in tqdm(runs, desc="Merge coverage records across runs"):
            with as_working_directory(r.work_path):
                with Pool(8) as p:
                    # Load registry
                    records = dict(
                        zip(coverage_files, p.map(load_registry, coverage_files))
                    )
                    # Create missing entries
                    for name, entry in records.items():
                        if name not in registries and entry is not None:
                            registries[name] = entry
                    # Merge registries with existing entries
                    p.starmap(
                        merge_registry, ((registries[n], records[n]) for n in records)
                    )
        #
        roots = collections.defaultdict(lambda: (0, 0))
        for path, registry in tqdm(
            registries.items(), desc="Compute coverage per metric"
        ):
            covered, total = roots[path.parent]
            roots[path.parent] = (registry.covered + covered, registry.total + total)
        for path, (covered, total) in sorted(roots.items()):
            print(path, covered, total, float(covered) / total)
        # Generate coverage report
        coverage_report = CoverageReport()
        for path, (coverage, total) in tqdm(
            roots.items(), desc="Generate coverage report"
        ):
            metric_type = path.parent.name
            combination_size = int(path.name)
            if metric_type == "atom":
                coverage_report.atom_coverage[combination_size] = CoverageRecord(
                    coverage, total
                )
            elif metric_type == "condition":
                coverage_report.condition_coverage[combination_size] = CoverageRecord(
                    coverage, total
                )
            elif metric_type == "predicate":
                coverage_report.predicate_coverage[combination_size] = CoverageRecord(
                    coverage, total
                )
            elif metric_type == "safety":
                coverage_report.safety_coverage[combination_size] = CoverageRecord(
                    coverage, total
                )
        return coverage_report

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
        # combinations = self.compute_events_combinations(trace)
        # self.compute_coverage(trace, monitor, combinations)
        return trace, self.safety_conditions


if __name__ == "__main__":
    SafecompControllerRunner.process_output(
        Path("../build/Unity_Data/StreamingAssets/CSI/Databases/messages.safety.db")
    )
