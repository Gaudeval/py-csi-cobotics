import contextlib
import os
from pathlib import Path

from csi.experiment import Repository, RunStatus
from csi.twin import DigitalTwinRunner


@contextlib.contextmanager
def as_working_directory(path):
    """Changes working directory and returns to previous on exit."""
    prev_cwd = Path.cwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(prev_cwd)


def collect_completed_runs(repository: Repository):
    for e in repository.experiments:
        assert isinstance(e, DigitalTwinRunner)
        for r in e.runs:
            if r.status == RunStatus.COMPLETE:
                yield e, r
