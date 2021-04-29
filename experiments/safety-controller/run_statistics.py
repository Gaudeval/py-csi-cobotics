"""Generate statistics on the runs in a repository"""

import collections
import json
import pickle

import seaborn
from pandas import DataFrame
from typing import List, Tuple, Dict
import seaborn as sns
import matplotlib.pyplot as mpl

from csi.configuration import ConfigurationManager
from csi.experiment import Repository, Experiment, Run, RunStatus

from wrapper.configuration import SafetyWorldConfiguration
from wrapper.runner import SafetyDigitalTwinRunner


def plot_waypoint_times(t: Repository):
    t: Repository
    e: Experiment
    r: Run
    # Wait times distribution
    wait_times: List[Tuple[str, float]] = []
    arrival_times: List[Tuple[str, float]] = []
    # Collect statistics across all runs
    for e, r in t.completed_runs:
        assert isinstance(e, SafetyDigitalTwinRunner)
        # Compute completion rate
        c: SafetyWorldConfiguration
        r = next(r for r in e.runs if r.status == RunStatus.COMPLETE)
        c = ConfigurationManager(SafetyWorldConfiguration).load(
            r.work_path / e.configuration_output
        )
        # Collect waypoints arrival and wait times
        a: float = 0.0
        for w in ["wp_start", "wp_bench", "wp_wait", "wp_cell", "wp_exit"]:
            d = getattr(c, w).duration
            wait_times.append((w, d))
            arrival_times.append((w, a))
            a += d

    j: DataFrame = DataFrame(wait_times, columns=["waypoint", "wait"])
    sns.displot(data=j, x="wait", hue="waypoint", col="waypoint")
    mpl.show()

    i: DataFrame = DataFrame(arrival_times, columns=["waypoint", "arrival"])
    sns.displot(data=i, x="arrival", hue="waypoint", col="waypoint")
    mpl.show()


def plot_coverage(t: Repository):
    e: Experiment
    r: Run
    # Use Case coverage
    uc_events_per_run = []
    # Collect statistics across all runs
    for e, r in t.completed_runs:
        assert isinstance(e, SafetyDigitalTwinRunner)
        with (r.work_path / e.use_cases_events).open("rb") as uc_events_file:
            x = pickle.load(uc_events_file)
            for use_case in x:
                for (condition, events) in x[use_case]:
                    uc_events_per_run.append((use_case, condition, events))

    # Merge use case events
    events_per_uc = {}
    for use_case, condition, events in uc_events_per_run:
        coverage_criterion = (use_case, tuple(condition))
        if coverage_criterion not in events_per_uc:
            events_per_uc[coverage_criterion] = events
        else:
            events_per_uc[coverage_criterion].merge(events)
    coverage_per_uc = [
        (use_case, str(condition), re.coverage)
        for (use_case, condition), re in events_per_uc.items()
    ]

    k: DataFrame = DataFrame(
        coverage_per_uc, columns=["use case", "criterion", "coverage"]
    )
    sns.relplot(
        data=k,
        style="criterion",
        hue="criterion",
        legend=True,
        col="use case",
        x="criterion",
        y="coverage",
    )
    mpl.show()


def plot_run_status(t: Repository):
    e: Experiment
    r: Run
    run_status = {s: 0 for s in RunStatus}
    for e in t.experiments:
        assert isinstance(e, SafetyDigitalTwinRunner)
        for r in e.runs:
            run_status[r.status] += 1

    data = sorted((s.name, v) for s, v in run_status.items() if v > 0)
    labels = [s for s, _ in data]
    values = [v for _, v in data]

    mpl.pie(values, labels=labels, normalize=True, shadow=False)
    mpl.axis("equal")
    mpl.title("Run completion status")
    mpl.show()


def plot_validation(t: Repository):
    e: Experiment
    r: Run
    error_counts = []
    for e, r in t.completed_runs:
        assert isinstance(e, SafetyDigitalTwinRunner)
        with (r.work_path / e.use_cases_classification).open() as uc_file:
            ucs: List[str]
            ucs = json.load(uc_file)
        with (r.work_path / "hazard-report.json").open() as report_file:
            report: Dict[str, bool]
            report = json.load(report_file)
        # run_errors = [v for v in report.values()].count(False)
        run_errors = tuple(sorted({k for k, v in report.items() if not v}))
        for uc in ucs:
            error_counts.append((uc, run_errors))

    data: DataFrame = DataFrame(error_counts, columns=["use case", "errors"])
    h = seaborn.histplot(data=data, x="use case", hue="errors", multiple="stack")
    h.set_title("Violations of validation properties per run")
    mpl.show()


if __name__ == "__main__":
    t: Repository
    t = Repository("./runs-replays")
    plot_run_status(t)
    # plot_waypoint_times(t)
    plot_coverage(t)
    plot_validation(t)
