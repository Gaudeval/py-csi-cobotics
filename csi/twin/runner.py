"""Experiment wrapper to run digital twin simulations"""

import json
import pickle
import shutil
import subprocess

from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

from csi.configuration import ConfigurationManager
from csi.experiment import Experiment
from csi.monitor import Monitor, Trace
from csi.safety import SafetyCondition
from csi.twin.configuration import DigitalTwinConfiguration


class DigitalTwinRunner(Experiment):
    """Digital twin experiment runner"""

    safety_conditions: List[SafetyCondition]
    configuration: DigitalTwinConfiguration

    configuration_output: Path = Path("assets/configuration.json")
    database_output: Path = Path("assets/database.sqlite")
    screenshot_output: Path = Path("assets/screenshots/")
    trace_output: Path = Path("events_trace.pkl")

    additional_output: Dict[str, Tuple[Path, Path]] = {}

    def clear_build_output(self):
        """Cleanup generated files in build folder"""
        self.configuration.build.configuration.unlink(missing_ok=True)
        self.configuration.build.database.unlink(missing_ok=True)
        shutil.rmtree(self.configuration.build.screenshots, ignore_errors=True)
        for (removed, _) in self.additional_output.values():
            (self.configuration.build.path / removed).unlink(missing_ok=True)

    def collect_build_output(self):
        """Collect generated files in build folder"""
        self.database_output.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(self.configuration.build.database, self.database_output)
        self.configuration_output.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(self.configuration.build.configuration, self.configuration_output)
        self.screenshot_output.parent.mkdir(parents=True, exist_ok=True)
        if self.configuration.build.screenshots.exists():
            shutil.copytree(
                self.configuration.build.screenshots,
                self.screenshot_output,
                dirs_exist_ok=True,
            )
        for (saved, backup) in self.additional_output.values():
            if (self.configuration.build.path / saved).exists():
                backup.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy(saved, backup)

    def execute(self) -> None:
        """Run digital twin build with specified configuration"""
        # Setup build and IO
        database_path = self.configuration.build.configuration
        executable_path = self.configuration.build.path / "Unity.exe"
        configuration_path = self.configuration.build.configuration
        self.clear_build_output()
        # Setup configuration
        if not configuration_path.parent.exists():
            configuration_path.parent.mkdir(parents=True, exist_ok=True)
        ConfigurationManager().save(self.configuration.world, configuration_path)
        # Run Unity build
        try:
            subprocess.run(str(executable_path), shell=True, check=True)
        finally:
            self.collect_build_output()
        # Check for hazard occurrence
        trace, conditions = self.process_output()
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
            print(type(safety_condition), safety_condition.uid)
            print(getattr(safety_condition, "description", ""))
            print("Occurs: ", i)
            report[safety_condition.uid] = i
        with open("./hazard-report.json", "w") as json_report:
            json.dump(report, json_report, indent=4)
        # Backup processed trace
        with self.trace_output.open("wb") as trace_file:
            pickle.dump(trace, trace_file)

    def process_output(self) -> Tuple[Trace, List[SafetyCondition]]:
        raise NotImplementedError
