from csi.experiment import Repository, Experiment, Run, RunStatus
from csi.twin import DigitalTwinRunner

from wrapper.utils import as_working_directory, collect_completed_runs

# TODO To library: experiment completed runs
# TODO To library: repository completed runs/experiments


if __name__ == "__main__":
    t: Repository = Repository("./runs")
    e: Experiment
    r: Run
    for e, r in collect_completed_runs(t):
        print(r.work_path)
        with as_working_directory(r.work_path):
            e.process_output()
