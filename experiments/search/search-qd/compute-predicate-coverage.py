import json
import pickle
import tqdm
from itertools import combinations
from typing import Iterable, Set, Dict
from pathlib import Path
from funcy import chain
from mtl.ast import AtomicPred, BinaryOpMTL, Node
from traces import TimeSeries

from csi.experiment import Repository, RunStatus
from csi.monitor import Monitor
from csi.safety import SafetyCondition
from scenarios.tcx import unsafe_control_actions, hazards, TcxBuildRunner


def extract_boolean_predicates(
    safety_conditions: Iterable[SafetyCondition],
) -> Set[Node]:
    terms: Set[AtomicPred] = set()
    comparisons: Set[BinaryOpMTL] = set()
    # Extract all candidates
    for s in safety_conditions:
        for p in s.condition.walk():
            if isinstance(p, AtomicPred):
                terms.add(p)
            if isinstance(p, BinaryOpMTL):
                comparisons.add(p)
    # Remove values used in comparisons
    for p in comparisons:
        terms.difference(p.children)
    return set(chain(terms, comparisons))


def save_coverage_info(output_path, coverage_info):
    with Path(output_path).open("w") as cache:
        json.dump(
            {
                "coverage": coverage_info[0] * 1.0 / coverage_info[1],
                "covered": coverage_info[0],
                "total": coverage_info[1],
            },
            cache,
        )


def compute_experiment_trace(experiment, output_path, conditions):
    predicates = sorted(extract_boolean_predicates(conditions))
    predicate_trace: Dict[int, Set[Node]] = {}
    output_cache = Path(output_path) / "cache" / "{}.pkl".format(experiment.uuid)
    # Load from cache if exists
    if output_cache.exists():
        with output_cache.open("rb") as cache:
            return pickle.load(cache)
    # Collect predicate trace
    for run in experiment.runs:
        if run.status == RunStatus.COMPLETE:
            # Load run trace
            run_db = run.work_path / "output.sqlite"
            run_trace, _ = TcxBuildRunner.process_output(run_db, conditions)
            # Compute predicate values at each point in time
            monitor = Monitor()
            for time, _ in TimeSeries.iter_merge(run_trace.values.values()):
                predicate_trace[time] = set()
                for p in predicates:
                    v = monitor.evaluate(run_trace, p, quantitative=False, time=time)
                    if v:
                        predicate_trace[time].add(p)
            break
    # Create experiment predicate trace cache
    output_cache.parent.mkdir(parents=True, exist_ok=True)
    with output_cache.open("bw") as cache:
        pickle.dump(predicate_trace, cache)
    #
    return predicate_trace


def compute_condition_trace(experiment, _, conditions):
    condition_trace = set()
    for run in experiment.runs:
        if run.status == RunStatus.COMPLETE:
            with (run.work_path / "hazard-report.json").open() as json_report:
                report = json.load(json_report)
                for uid, occurs in report.items():
                    if occurs is not None:
                        occurs = float(occurs)
                        occurs = min(1, max(0, occurs))
                        if occurs >= 1 and uid in {c.uid for c in conditions}:
                            condition_trace.add(uid)
            break
    return condition_trace


def compute_coverage(repository_path, output_path, safety_conditions, coverage_group=2):
    repository = Repository(repository_path)
    predicates = sorted(extract_boolean_predicates(safety_conditions))
    # Create output and cache folders
    output_path = Path(output_path)
    output_path.mkdir(parents=True, exist_ok=True)
    # Collect encountered predicates at every point in time per experiment
    # Collect encountered conditions per experiment
    predicate_traces = []
    condition_traces = []
    for experiment in tqdm.tqdm(repository.experiments, desc="Experiment", total=1000):
        predicate_traces.append(
            compute_experiment_trace(experiment, output_path, safety_conditions)
        )
        condition_traces.append(
            compute_condition_trace(experiment, output_path, safety_conditions)
        )
    # Record encountered predicate values
    predicate_values_cache = output_path / "predicates_{}.pkl".format(coverage_group)
    if predicate_values_cache.exists():
        with predicate_values_cache.open("rb") as cache:
            predicate_values = pickle.load(cache)
    else:
        predicate_values = {p: set() for p in combinations(predicates, coverage_group)}
        for trace in tqdm.tqdm(predicate_traces, desc="Predicates"):
            for satisfied in trace.values():
                for predicate_group in predicate_values:
                    predicate_values[predicate_group].add(
                        tuple(p in satisfied for p in predicate_group)
                    )
        with predicate_values_cache.open("wb") as cache:
            pickle.dump(predicate_values, cache)
    # Record condition values
    condition_values_cache = output_path / "conditions_{}.pkl".format(coverage_group)
    if condition_values_cache.exists():
        with condition_values_cache.open("rb") as cache:
            condition_values = pickle.load(cache)
    else:
        condition_uids = [u.uid for u in safety_conditions]
        condition_values = {
            p: set() for p in combinations(condition_uids, coverage_group)
        }
        for satisfied in condition_traces:
            for condition_group in tqdm.tqdm(condition_values, desc="Conditions"):
                condition_values[condition_group].add(
                    tuple(p in satisfied for p in condition_group)
                )
        with condition_values_cache.open("wb") as cache:
            pickle.dump(condition_values, cache)
    # Compute coverage metrics
    predicate_coverage = (
        sum(len(s) for s in predicate_values.values()),
        len(predicate_values) * 2 ** coverage_group,
    )
    save_coverage_info(
        output_path / "predicate_coverage_{}.json".format(coverage_group),
        predicate_coverage,
    )
    condition_coverage = (
        sum(len(s) for s in condition_values.values()),
        len(condition_values) * 2 ** coverage_group,
    )
    save_coverage_info(
        output_path / "condition_coverage_{}.json".format(coverage_group),
        condition_coverage,
    )
    safety_coverage = (
        len({t for s in condition_traces for t in s}),
        len(safety_conditions),
    )
    save_coverage_info(
        output_path / "safety_coverage_{}.json".format(coverage_group),
        safety_coverage,
    )
    return predicate_coverage, condition_coverage, safety_coverage


if __name__ == "__main__":
    conditions = list(chain(unsafe_control_actions, hazards))
    #
    results = {}

    for s in range(1, 3):
        for runs in tqdm.tqdm(
            [
                "./backup-4-stop in cell/runs",  # Experiment 1000/1000 // Run 1/1 // Coverage 1854/3960
                "./backup-3-no stop in cell/runs",  # Experiment 1000/1000 // Run 1/1 // Coverage 1855/3960
                "../search-ga/backup-1-minimise/runs",  # ../search-ga/backup-1-minimise/runs 1827 3960 0.46136363636363636
                "../search-ga/backup-2-maximise/runs",  # ../search-ga/backup-2-maximise/runs 1841 3960 0.4648989898989899
            ],
            desc="Runs",
        ):
            results[runs] = compute_coverage(
                runs, Path(runs).parent / "coverage", conditions, s
            )
        #
        for runs in results:
            coverage = results[runs]
            print(runs, coverage)
