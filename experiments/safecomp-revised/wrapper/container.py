import json
import pickle
import tempfile
import shutil

from pathlib import Path
from typing import Tuple, List

import docker

from csi.configuration import ConfigurationManager
from csi.experiment import Experiment
from csi.monitor import Trace, Monitor
from csi.safety import SafetyCondition
from csi.twin import DigitalTwinConfiguration


class TwinContainerRunner(Experiment):
    configuration: DigitalTwinConfiguration
    image_name: str

    # Collected or generated run files
    configuration_output = Path("assets/configuration.json")
    database_output = Path("assets/database.sqlite")
    trace_output: Path = Path("events_trace.pkl")

    def collect_output(self, configuration_path, database_path):
        """Collect generated files in build folder"""
        self.database_output.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(database_path, self.database_output)
        self.configuration_output.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(configuration_path, self.configuration_output)

    def execute(self) -> None:
        """Run digital twin container with the specified configuration"""
        with tempfile.TemporaryDirectory() as configuration_root, tempfile.TemporaryDirectory() as database_root:
            # Setup configuration
            configuration_dir = Path(configuration_root)
            configuration_file = self.configuration.build.configuration.name
            configuration_path = configuration_dir / configuration_file
            ConfigurationManager().save(self.configuration.world, configuration_path)
            # Setup database output
            database_dir = Path(database_root)
            database_file = self.configuration.build.database.name
            database_path = database_dir / database_file
            # Run twin container
            try:
                client = docker.from_env()
                logs = client.containers.run(
                    self.image_name,
                    auto_remove=True,
                    volumes={
                        str(configuration_dir.absolute()): {
                            "bind": "/csi/configuration",
                            "mode": "rw",
                        },
                        str(database_dir.absolute()): {
                            "bind": "/csi/databases",
                            "mode": "rw",
                        },
                    },
                    working_dir=str(self.path.absolute()),
                    stdout=True,
                    stderr=True,
                )
                print(logs)
            finally:
                self.collect_output(configuration_path, database_path)
        # Check for hazard occurrence
        trace, conditions = self.process_output()
        self.produce_safety_report(trace, conditions)
        # Backup processed trace
        with self.trace_output.open("wb") as trace_file:
            pickle.dump(trace, trace_file)

    def produce_safety_report(self, trace, conditions, quiet=False):
        report = {}
        safety_condition: SafetyCondition
        for safety_condition in conditions:
            i = Monitor().evaluate(
                trace,
                safety_condition.condition,
                dt=0.01,
                quantitative=self.configuration.ltl.quantitative,
                logic=self.configuration.ltl.logic,
            )
            if not quiet:
                print(type(safety_condition), safety_condition.uid)
                print(getattr(safety_condition, "description", ""))
                print("Occurs: ", i)
            report[safety_condition.uid] = i
        with open("./hazard-report.json", "w") as json_report:
            json.dump(report, json_report, indent=4)
        return report

    def process_output(self) -> Tuple[Trace, List[SafetyCondition]]:
        raise NotImplementedError
