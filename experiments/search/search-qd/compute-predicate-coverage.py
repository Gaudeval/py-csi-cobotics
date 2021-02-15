from itertools import combinations
from typing import Iterable, Set
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


def compute_coverage(repository_path, safety_conditions, group_size=2):
    repository = Repository(repository_path)
    predicates = sorted(extract_boolean_predicates(safety_conditions))
    predicate_values = {p: set() for p in combinations(predicates, group_size)}
    #
    coverage_count = 2 ** group_size * (len(predicate_values))
    experiment_count = len(list(repository.experiments))
    for i, experiment in enumerate(repository.experiments, start=1):
        run_count = len(list(experiment.runs))
        for j, run in enumerate(experiment.runs, start=1):
            if run.status == RunStatus.COMPLETE:
                run_db = run.work_path / "output.sqlite"
                run_trace, _ = TcxBuildRunner.process_output(run_db, safety_conditions)
                #
                monitor = Monitor()
                for time, _ in TimeSeries.iter_merge(run_trace.values.values()):
                    v = dict()
                    # Compute individual predicate values
                    for p in predicates:
                        v[p] = (
                            monitor.evaluate(
                                run_trace, p, quantitative=False, time=time
                            ),
                        )
                    # Record encountered values combination
                    for predicate_group in predicate_values:
                        predicate_values[predicate_group].add(
                            tuple(v[p] for p in predicate_group)
                        )

                #
                coverage = sum(len(v) for v in predicate_values.values())
                print(
                    f"Experiment {i}/{experiment_count} // Run {j}/{run_count} // Coverage {coverage}/{coverage_count}"
                )
    return coverage, coverage_count


if __name__ == "__main__":
    conditions = list(chain(unsafe_control_actions, hazards))
    #
    results = {}
    for runs in [
        "./backup-4-stop in cell/runs",
        "./backup-3-no stop in cell/runs",
        "../search-ga/backup-1-minimise",
        "../search-ga/backup-2-maximise",
    ]:
        encountered, total = compute_coverage(runs, conditions)
        results[runs] = (encountered, total)
    #
    for runs in results:
        encountered, total = results[runs]
        print(runs, encountered, total, encountered * 1.0 / total)
