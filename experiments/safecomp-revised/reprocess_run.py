"""Reprocess the runs from a given repository which match the given condition"""

import contextlib
import os
import pickle
import tqdm

from pathlib import Path

from csi.experiment import Repository, Experiment, Run
from csi.twin import DigitalTwinRunner
from wrapper.runner import SafecompControllerRunner


def needs_processing(e: Experiment, r: Run):
    return True


def reprocess(e: SafecompControllerRunner):
    with contextlib.redirect_stdout(None), contextlib.redirect_stderr(None):
        # Check for hazard occurrence
        trace, conditions = e.process_output()
        e.produce_safety_report(trace, conditions)
        # Backup processed trace
        with e.trace_output.open("wb") as trace_file:
            pickle.dump(trace, trace_file)


if __name__ == "__main__":
    REPOSITORY_PATH = Path("./runs")
    #
    r: Run
    e: Experiment
    t: Repository
    t = Repository(REPOSITORY_PATH)
    for e in tqdm.tqdm(t.experiments):
        assert isinstance(e, SafecompControllerRunner)
        for r in e.runs:
            if needs_processing(e, r):
                cwd = os.getcwd()
                try:
                    os.chdir(r.work_path)
                    reprocess(e)
                finally:
                    # Reset current directory
                    os.chdir(cwd)
