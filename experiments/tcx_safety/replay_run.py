"""Replay the runs from a given repository which match the given condition"""

import json
from pathlib import Path

from csi import Repository, Experiment, Run, ConfigurationManager
from wrapper.runner import SafecompControllerRunner
from wrapper.configuration import (
    SceneConfiguration,
    BuildConfiguration,
    MonitorConfiguration,
    RunnerConfiguration,
)


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
                cfg_build = BuildConfiguration(BUILD_PATH)
                cfg_world = ConfigurationManager(SceneConfiguration).load(
                    r.work_path / e.configuration_output
                )
                cfg_logic = MonitorConfiguration(
                    j["ltl"]["connective"], j["ltl"]["quantitative"]
                )
                cfg_run = RunnerConfiguration(cfg_world, cfg_build, cfg_logic)
                #
                s = SafecompControllerRunner(REPLAY_PATH, cfg_run)
                s.run()
                exit(0)
