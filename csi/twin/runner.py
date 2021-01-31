"""Experiment wrapper to run digital twin simulations"""

import dataclasses
import json
import shutil
import subprocess

from pathlib import Path
from typing import List, Optional, Tuple, Union

from csi.configuration import ConfigurationManager
from csi.experiment import Experiment
from csi.monitor import Monitor
from csi.monitor.trace import Trace
from csi.safety import SafetyCondition
from csi.twin.converter import (
    ObstructionDetection,
    RegionConverter,
    DropKey,
    DropTable,
    ConverterType,
    FilterType,
)
from csi.twin.importer import DBMessageImporter
from csi.twin.orm import DataBase
from csi.scenarios.tcx.safety.hazards import hazards
from csi.scenarios.tcx.safety.ucas import unsafe_control_actions
from csi.scenarios.tcx.safety.entities import EntityPosition
from csi.scenarios.tcx.configuration import WorldData


@dataclasses.dataclass
class BuildRunnerConfiguration:
    """Digital twin experiment configuration"""

    build: Path = dataclasses.field(default_factory=Path)
    world: WorldData = dataclasses.field(default_factory=WorldData)


class BuildRunner(Experiment):
    """Digital twin experiment runner"""

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
        # Restrict monitor to prototype hazard and uca
        hazard = next((h for h in hazards if h.name == "H3"))
        uca = next((u for u in unsafe_control_actions if u.uid == "UCA9-P-2"))
        # Check for hazard occurrence
        trace, conditions = self.process_output(twin_files["db"][1], [hazard, uca])
        report = {}
        safety_condition: SafetyCondition
        for safety_condition in conditions:
            i = trace.evaluate(safety_condition.condition)
            print(type(safety_condition), safety_condition.uid)
            print(safety_condition.description)
            print("Occurs: ", i)
            report[safety_condition.uid] = i
        with open("./hazard-report.json", "w") as json_report:
            json.dump(report, json_report, indent=4)

    @staticmethod
    def process_output(
        database_path: Union[str, Path],
        conditions: Optional[List[SafetyCondition]] = None,
    ) -> Tuple[Trace, List[SafetyCondition]]:
        """Extract values from simulation message trace"""
        # FIXME Move to twin-specific library for tcx case study
        # Load default conditions
        if conditions is None:
            conditions = []
            conditions.extend(hazards)
            conditions.extend(unsafe_control_actions)
        # Define safety monitor
        monitor = Monitor()
        for safety_condition in conditions:
            monitor += safety_condition.condition
        # Import configuration
        entity_aliases = {
            "Tim_Operator_0": "operator",
            "ur10_UR10_0": "cobot",
            "Spot Welder Assembly_StaticEntity_0": "tool",
            "Component Assembly_StaticEntity_2": "assembly",
        }
        region_aliases = {
            "Enclosure Region": EntityPosition.WORKSPACE,
            "Spot Welder Region": EntityPosition.TOOL,
            "Loading Platform Region": EntityPosition.BENCH,
        }
        region_names = {
            "Enclosure Region": "workspace",
            "Spot Welder Region": "tool",
            "Loading Platform Region": "bench",
        }
        workspace_entities = {
            k.replace("_", "-")
            for k, v in entity_aliases.items()
            if v in ["cobot", "tool"]
        }
        converters: List[
            Tuple[
                Optional[FilterType],
                ConverterType,
            ]
        ]
        converters = [
            (
                (lambda m: (m["__table__"] == "regionstatus")),
                ObstructionDetection("Enclosure Region", workspace_entities),
            ),
            (
                (lambda m: (m["__table__"] == "regionstatus")),
                RegionConverter("region", "entity_id", region_names),
            ),
            (
                (lambda m: (m["__table__"] == "positionstatus")),
                RegionConverter("region", "position", region_aliases),
            ),
            (None, DropTable("triggerregionexitevent", "triggerregionenterevent")),
            (
                None,
                DropKey(
                    "id",
                    "collider",
                    "collision_force",
                    "parent_id",
                    "entity",
                    "region",
                    "entities",
                ),
            ),
        ]
        # Import trace
        database = DataBase(database_path)
        trace = Trace(monitor)
        message_importer = DBMessageImporter(entity_aliases, converters)
        message_importer.import_messages(trace, database)
        return trace, conditions
