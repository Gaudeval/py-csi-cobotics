from csi.experiment import Repository, Experiment, Run

from wrapper.utils import as_working_directory
from wrapper.runner import SafetyDigitalTwinRunner


if __name__ == "__main__":
    t: Repository = Repository("./runs")
    e: Experiment
    r: Run
    for e, r in t.completed_runs:
        assert isinstance(e, SafetyDigitalTwinRunner)
        print(r.work_path)
        with as_working_directory(r.work_path):
            e.process_output()
