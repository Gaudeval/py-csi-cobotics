"""Replay the runs from a given repository which match the given condition"""

import json

from pathlib import Path
from typing import Optional

from csi.configuration import ConfigurationManager
from csi.experiment import Repository, Experiment, Run, RunStatus
from wrapper.configuration import SceneConfiguration, BuildConfiguration, RunnerConfiguration
from wrapper.runner import SafetyDigitalTwinRunner


def classified_as(e: SafetyDigitalTwinRunner, r: Run, uc: str):
    with (r.work_path / e.use_cases_classification).open() as uc_file:
        ucs = json.load(uc_file)
    return uc in ucs


def satisfies_property(_, r: Run, p: Optional[str] = None):
    with (r.work_path / "hazard-report.json").open() as report_file:
        report = json.load(report_file)
    if p is None:
        return all(report.values())
    else:
        return report[p]


if __name__ == "__main__":
    BUILD_PATH = Path("./build-server").absolute()
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
            # if not classified_as(e, r, "U1"):
            if not satisfies_property(e, r, None):
                print(r.path)
                w = ConfigurationManager(SceneConfiguration).load(
                    r.work_path / e.configuration_output
                )
                c = RunnerConfiguration(w, BuildConfiguration(BUILD_PATH))
                s = SafetyDigitalTwinRunner(REPLAY_PATH, c)
                s.run()
                exit(0)
