import pickle

from pandas import DataFrame
from typing import List, Tuple
import seaborn as sns
import matplotlib.pyplot as mpl

from csi.configuration import ConfigurationManager
from csi.experiment import Repository, Experiment, Run, RunStatus
from csi.twin import DigitalTwinRunner

from wrapper.configuration import SafetyWorldConfiguration

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
    # Collect statistics across all runs
    t = Repository("./runs")
    for e in t.experiments:
        assert isinstance(e, DigitalTwinRunner)
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
            with (r.work_path / "events_trace.pkl").open("rb") as s:
                x = pickle.load(s)

    print(f"{completed_experiments} / {total_experiments}")

    j: DataFrame = DataFrame(wait_times, columns=["waypoint", "wait"])
    sns.displot(data=j, x="wait", hue="waypoint", col="waypoint")
    mpl.show()

    i: DataFrame = DataFrame(arrival_times, columns=["waypoint", "arrival"])
    sns.displot(data=i, x="arrival", hue="waypoint", col="waypoint")
    mpl.show()
