import contextlib
import datetime
import enum
import json
import os
import pathlib
import pickle
import random
import traceback
import typing
import uuid

import csi.configuration


class RunStatus(enum.Enum):
    """Status and result of an experiment run"""

    PENDING = 0
    RUNNING = 1
    COMPLETE = 2
    FAILED = 3


class Run:
    """Experiment run record and output folder."""

    def __init__(self, experiment):
        self.uuid = uuid.uuid4().int
        self.experiment = experiment
        # Metadata
        self.status = RunStatus.PENDING
        self.time_start = None
        self.time_complete = None

    @classmethod
    def load(cls, path) -> "Run":
        """Load run record from local directory."""
        path = pathlib.Path(path)
        experiment = Experiment.load(path.parent.parent)
        run = Run(experiment)
        run.uuid = int(path.stem)
        # Load metadata
        with (run.path / "metadata.json").open() as metadata_file:
            metadata = json.load(metadata_file)
        run.status = RunStatus[metadata["status"]]
        run.time_start = metadata["time"]["start"]
        run.time_complete = metadata["time"]["complete"]
        return run

    @property
    def metadata(self):
        return {
            "status": self.status.name,
            "time": {"start": self.time_start, "complete": self.time_complete},
        }

    @property
    def path(self):
        return self.experiment.path / "runs" / str(self.uuid)

    @property
    def work_path(self):
        return self.path / "workdir"

    def prepare_path(self):
        """Create run root directories and metadata files"""
        # Create directories
        self.work_path.mkdir(parents=True, exist_ok=True)
        # Create metadata
        self.update_metadata()

    def update_metadata(self):
        """Update metadata record on disk"""
        with (self.path / "metadata.json").open("w") as metadata_file:
            json.dump(self.metadata, metadata_file)

    def execute(self):
        """Run attached experiment tracking run status and log."""
        self.prepare_path()
        # Redirect output to run log file
        with (self.path / "log").open("w") as stdout:
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stdout):
                cwd = os.getcwd()
                try:
                    os.chdir(self.work_path)
                    # Update metadata
                    self.time_start = datetime.datetime.now().strftime(
                        "%d/%m/%Y %H:%M:%S"
                    )
                    self.status = RunStatus.RUNNING
                    self.update_metadata()
                    # Run experiment
                    self.experiment.execute()
                    # Update status
                    self.status = RunStatus.COMPLETE
                except Exception as _:
                    # Record failure and exception
                    self.status = RunStatus.FAILED
                    traceback.print_exc()
                    raise
                finally:
                    # Reset current directory
                    os.chdir(cwd)
                    # Update metadata
                    self.time_complete = datetime.datetime.now().strftime(
                        "%d/%m/%Y %H:%M:%S"
                    )
                    self.update_metadata()


class Experiment:
    def __init__(self, root, configuration):
        self.uuid = uuid.uuid4().int
        self.root = pathlib.Path(root).absolute()
        self.configuration = configuration

    @staticmethod
    def load(path):
        """Load experiment record from local directory."""
        path = pathlib.Path(path)
        with (path / "experiment.pkl").open("rb") as pickle_file:
            experiment = pickle.load(pickle_file)
            if experiment.path != path:
                experiment.root = path.parent
        return experiment

    @property
    def path(self):
        return pathlib.Path(self.root) / "{}-{}".format(type(self).__name__, self.uuid)

    def prepare_path(self):
        """Create experiment root directories and metadata files"""
        # Create directory
        (self.path / "runs").mkdir(parents=True, exist_ok=True)
        # Save configuration
        csi.configuration.ConfigurationManager().save(
            self.configuration, self.path / "configuration.json"
        )
        # Save experiment object
        with (self.path / "experiment.pkl").open("wb") as pickle_file:
            pickle.dump(self, pickle_file)

    def run(self, retries: int = 1) -> None:
        """Attempt to run the experiment recording run results"""
        self.prepare_path()
        for _ in range(retries):
            try:
                Run(self).execute()
                break
            except Exception as _:
                pass

    def execute(self):
        """Experiment entry point as defined by the end-user"""
        raise NotImplementedError()

    @property
    def runs(self) -> typing.Iterator[Run]:
        for i in (self.path / "runs").iterdir():
            run = Run.load(i)
            yield run


class Repository:
    """Record of an experiment set"""

    def __init__(self, path):
        self.path = pathlib.Path(path)

    @property
    def experiments(self):
        for i in self.path.iterdir():
            if i.is_dir():
                yield Experiment.load(i)

    @property
    def completed_runs(self):
        for e in self.experiments:
            for r in e.runs:
                if r.status == RunStatus.COMPLETE:
                    yield e, r


class WorkingExperiment(Experiment):
    def execute(self):
        with open("./results.txt", "w") as results_file:
            results_file.write(str(uuid.uuid4().int))


class FailingExperiment(Experiment):
    def execute(self):
        raise NotImplementedError()


class RandomExperiment(Experiment):
    def execute(self):
        i = random.random()
        print(i)
        if i < 0.5:
            raise NotImplementedError()
        else:
            with open("./results.txt", "w") as results_file:
                results_file.write(str(self.configuration["input"]) + "\n")
                results_file.write(str(uuid.uuid4().int))


if __name__ == "__main__":
    experiment_root = pathlib.Path("../tests/experiments")
    # Cleanup test directory
    if experiment_root.exists():
        import shutil

        shutil.rmtree(experiment_root)
    # Create example experiments
    x = WorkingExperiment(experiment_root, {"input": True, "working": True})
    x.run()
    y = FailingExperiment(experiment_root, {"input": True, "working": False})
    y.run(5)
    z = RandomExperiment(experiment_root, {"input": True, "working": "Maybe"})
    z.run(10)
    # Reload experiments from repository
    repository = Repository(experiment_root)
    for e in repository.experiments:
        print("-----")
        print(type(e))
        print(e.configuration)
        for r in e.runs:
            print(r.metadata)
    # Load run without specifying experiment
    print("-----")
    e = next(repository.path.iterdir())
    r = next((e / "runs").iterdir())
    r = Run.load(r)
    print(r.path)
    print(r.metadata)
