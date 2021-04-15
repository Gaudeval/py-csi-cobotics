"""Experiment wrapper to run digital twin simulations"""

import json
import shutil
import subprocess

from pathlib import Path
from typing import List, Optional, Tuple, Union

from csi.configuration import ConfigurationManager
from csi.experiment import Experiment
from csi.monitor import Monitor, Trace
from csi.safety import SafetyCondition
from csi.twin.configuration import DigitalTwinConfiguration


class DigitalTwinRunner(Experiment):
    """Digital twin experiment runner"""

    safety_conditions: List[SafetyCondition]
    configuration: DigitalTwinConfiguration

    def execute(self) -> None:
        """Run digital twin build with specified configuration"""
        # Setup build and IO
        twin_files = {
            "shot": (
                self.configuration.build.assets / "Screenshots" / "scene.png",
                Path("./scene.png"),
            ),
        }
        binary = self.configuration.build.path / "Unity.exe"
        # Cleanup generated files
        for (removed, _) in twin_files.values():
            removed.unlink(missing_ok=True)
        # Setup configuration
        if not self.configuration.build.configuration.parent.exists():
            self.configuration.build.configuration.parent.mkdir(
                parents=True, exist_ok=True
            )
        ConfigurationManager().save(
            self.configuration.world, self.configuration.build.configuration
        )
        # Run Unity build
        try:
            subprocess.run(str(binary), shell=True, check=True)
        finally:
            # Backup generated files
            Path("assets").mkdir(parents=True, exist_ok=True)
            shutil.copy(
                self.configuration.build.configuration,
                Path("assets/configuration.json"),
            )
            shutil.copy(
                self.configuration.build.database, Path("assets/database.sqlite")
            )
            for (saved, backup) in twin_files.values():
                if saved.exists():
                    shutil.copy(saved, backup)
        # Check for hazard occurrence
        trace, conditions = self.process_output(
            Path("assets/database.sqlite"), self.safety_conditions
        )
        report = {}
        safety_condition: SafetyCondition
        for safety_condition in conditions:
            i = Monitor().evaluate(
                trace,
                safety_condition.condition,
                quantitative=self.configuration.ltl.quantitative,
                logic=self.configuration.ltl.logic,
            )
            print(type(safety_condition), safety_condition.uid)
            print(getattr(safety_condition, "description", ""))
            print("Occurs: ", i)
            report[safety_condition.uid] = i
        with open("./hazard-report.json", "w") as json_report:
            json.dump(report, json_report, indent=4)

    @staticmethod
    def process_output(
        database_path: Union[str, Path],
        safety_conditions: Optional[List[SafetyCondition]] = None,
    ) -> Tuple[Trace, List[SafetyCondition]]:
        raise NotImplementedError
