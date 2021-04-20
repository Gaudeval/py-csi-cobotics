from csi.experiment import Repository, Experiment, Run, RunStatus
from csi.twin import DigitalTwinRunner

from wrapper.utils import as_working_directory

if __name__ == "__main__":
    t: Repository = Repository("./runs")
    e: Experiment
    r: Run
    for e, r in t.completed_runs:
        assert isinstance(e, DigitalTwinRunner)
        print(r.work_path)
        with as_working_directory(r.work_path):
            e.process_output()
