"""Replay the runs from a given repository which match the given condition"""

import json
from pathlib import Path

from csi.configuration import ConfigurationManager
from csi.experiment import Repository, Experiment, Run
from csi.twin.configuration import DigitalTwinConfiguration, TemporalLogicConfiguration
from wrapper.runner import SafecompControllerRunner
from wrapper.configuration import SafetyWorldConfiguration, SafetyBuildConfiguration


def needs_replaying(e: Experiment, r: Run):
    return True


if __name__ == "__main__":
    BUILD_PATH = Path("./build-x2").absolute()
    REPOSITORY_PATH = Path("./runs")
    REPLAY_PATH = Path("./runs-replays")
    #
    r: Run
    e: Experiment
    t: Repository
    t = Repository(REPOSITORY_PATH)
    for e in t.experiments:
        assert isinstance(e, SafecompControllerRunner)
        for r in e.runs:
            if needs_replaying(e, r):
                print(r.path)
                j = json.load((e.path / "configuration.json").open("r"))
                # Run configuration
                cfg_build = SafetyBuildConfiguration(BUILD_PATH)
                cfg_world = ConfigurationManager(SafetyWorldConfiguration).load(
                    r.work_path / e.configuration_output
                )
                cfg_logic = TemporalLogicConfiguration(
                    j["ltl"]["connective"], j["ltl"]["quantitative"]
                )
                cfg_run = DigitalTwinConfiguration(cfg_world, cfg_build, cfg_logic)
                #
                s = SafecompControllerRunner(REPLAY_PATH, cfg_run)
                s.run()
                exit(0)
