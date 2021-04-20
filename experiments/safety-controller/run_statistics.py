import pickle

from pandas import DataFrame
from typing import List, Tuple
import seaborn as sns
import matplotlib.pyplot as mpl

from csi.configuration import ConfigurationManager
from csi.experiment import Repository, Experiment, Run, RunStatus

from wrapper.configuration import SafetyWorldConfiguration
from wrapper.runner import SafetyDigitalTwinRunner


if __name__ == "__main__":
    t: Repository
    e: Experiment
    r: Run
    # Completion rate
    total_experiments = 0
    completed_experiments = 0
    # Wait times distribution
    wait_times: List[Tuple[str, float]] = []
    arrival_times: List[Tuple[str, float]] = []
    # Use Case coverage
    uc_events_per_run = []
    # Collect statistics across all runs
    t = Repository("./runs")
    for e in t.experiments:
        assert isinstance(e, SafetyDigitalTwinRunner)
        # Compute completion rate
        completed = any(r.status == RunStatus.COMPLETE for r in e.runs)
        total_experiments += 1
        completed_experiments += 1 if completed else 0
        #
        if completed:
            # Load run configuration
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
            #
            with (r.work_path / e.use_cases_events).open("rb") as uc_events_file:
                x = pickle.load(uc_events_file)
                for use_case in x:
                    for (condition, events) in x[use_case]:
                        uc_events_per_run.append((use_case, condition, events))

    print(f"{completed_experiments} / {total_experiments}")

    j: DataFrame = DataFrame(wait_times, columns=["waypoint", "wait"])
    sns.displot(data=j, x="wait", hue="waypoint", col="waypoint")
    # mpl.show()

    i: DataFrame = DataFrame(arrival_times, columns=["waypoint", "arrival"])
    sns.displot(data=i, x="arrival", hue="waypoint", col="waypoint")
    # mpl.show()

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
