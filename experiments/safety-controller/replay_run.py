from pathlib import Path

from csi.configuration import ConfigurationManager
from csi.experiment import Repository, Experiment, Run, RunStatus
from csi.twin.configuration import DigitalTwinConfiguration
from wrapper.configuration import SafetyWorldConfiguration, SafetyBuildConfiguration
from wrapper.runner import SafetyDigitalTwinRunner


if __name__ == "__main__":
    BUILD_PATH = Path("./build").absolute()
    REPOSITORY_PATH = Path("./runs")
    REPLAY_PATH = Path("./runs-replays")
    #
    r: Run
    e: Experiment
    t: Repository
    t = Repository(REPOSITORY_PATH)
    for e in t.experiments:
        assert isinstance(e, SafetyDigitalTwinRunner)
        for r in e.runs:
            if r.status != RunStatus.COMPLETE:
                print(r.path)
                w = ConfigurationManager(SafetyWorldConfiguration).load(
                    r.work_path / e.configuration_output
                )
                c = DigitalTwinConfiguration(w, SafetyBuildConfiguration(BUILD_PATH))
                s = SafetyDigitalTwinRunner(REPLAY_PATH, c)
                s.run()
