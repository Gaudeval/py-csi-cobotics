"""Experiment wrapper to run digital twin simulations"""

import dataclasses
import json
import shutil
import subprocess

from pathlib import Path
from typing import Any, List, Optional, Tuple, Union

from csi.configuration import ConfigurationManager
from csi.experiment import Experiment
from csi.monitor import Monitor, Trace
from csi.safety import SafetyCondition


@dataclasses.dataclass
class BuildRunnerConfiguration:
    """Digital twin experiment configuration"""

    world: Any
    build: Path = dataclasses.field(default_factory=Path)


class BuildRunner(Experiment):
    """Digital twin experiment runner"""

    safety_conditions: List[SafetyCondition]
    configuration: BuildRunnerConfiguration

    @property
    def assets_path(self) -> Path:
        """Location of simulation assets in build"""
        return self.configuration.build / "Unity_Data" / "StreamingAssets" / "CSI"

    def execute(self) -> None:
        """Run digital twin build with specified configuration"""
        # Setup build and IO
        twin_files = {
            "db": (
                self.assets_path / "Databases" / "csi.prototype.sqlite",
                Path("./output.sqlite"),
            ),
            "cfg": (
                self.assets_path / "Configuration" / "csi.json",
                Path("./configuration.json"),
            ),
            "shot": (
                self.assets_path / "Screenshots" / "scene.png",
                Path("./scene.png"),
            ),
        }
        binary = self.configuration.build / "Unity.exe"
        # Cleanup generated files
        for (removed, _) in twin_files.values():
            removed.unlink(missing_ok=True)
        # Setup configuration
        if not twin_files["cfg"][0].parent.exists():
            twin_files["cfg"][0].parent.mkdir(parents=True, exist_ok=True)
        ConfigurationManager().save(self.configuration.world, twin_files["cfg"][0])
        # Run Unity build
        try:
            subprocess.run(str(binary), shell=True, check=True)
        finally:
            # Backup generated files
            for (saved, backup) in twin_files.values():
                if saved.exists():
                    shutil.copy(saved, backup)
        # Check for hazard occurrence
        trace, conditions = self.process_output(
            twin_files["db"][1], self.safety_conditions
        )
        report = {}
        safety_condition: SafetyCondition
        for safety_condition in conditions:
            i = Monitor().evaluate(trace, safety_condition.condition)
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
