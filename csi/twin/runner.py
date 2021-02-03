"""Experiment wrapper to run digital twin simulations"""

import dataclasses
import json
import shutil
import subprocess

from pathlib import Path
from typing import List, Optional, Tuple, Union

from traces import TimeSeries

from csi.configuration import ConfigurationManager
from csi.experiment import Experiment
from csi.monitor import Monitor, Trace
from csi.safety import SafetyCondition
from csi.safety.stpa import Hazard, UnsafeControlAction
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
from scenarios.tcx import hazards, unsafe_control_actions, WorldData


def cobot_reaches_target(m):
    m["entity_id"] = "cobot"
    m["reaches_target"] = True
    return m


def cobot_has_target(m):
    m["entity_id"] = "cobot"
    m["has_target"] = True
    return m


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
        hazard = next((h for h in hazards if h.uid == 3))
        uca = next((u for u in unsafe_control_actions if u.uid == "UCA9-P-2"))
        # Check for hazard occurrence
        trace, conditions = self.process_output(twin_files["db"][1], [hazard, uca])
        report = {}
        safety_condition: Union[Hazard, UnsafeControlAction]
        for safety_condition in conditions:
            i = Monitor().evaluate(trace, safety_condition.condition)
            print(type(safety_condition), safety_condition.uid)
            print(safety_condition.description)
            print("Occurs: ", i)
            report[safety_condition.uid] = i
        with open("./hazard-report.json", "w") as json_report:
            json.dump(report, json_report, indent=4)

    @staticmethod
    def process_output(
        database_path: Union[str, Path],
        safety_conditions: Optional[List[SafetyCondition]] = None,
    ) -> Tuple[Trace, List[SafetyCondition]]:
        """Extract values from simulation message trace"""
        # FIXME Move to twin-specific library for tcx case study
        # Load default conditions
        if safety_conditions is None:
            safety_conditions = []
            safety_conditions.extend(hazards)
            safety_conditions.extend(unsafe_control_actions)
        # Define safety monitor
        monitor = Monitor()
        for safety_condition in safety_conditions:
            monitor += safety_condition.condition
        # Import configuration
        entity_aliases = {
            "Tim_Operator": "operator",
            "ur10_cobot": "cobot",
            "Spot Welder Assembly_welder": "tool",
            "TT7302_mandrel_assembly": "assembly",
        }
        region_names = {
            "Work Cell Region": "in_workspace",
            "Spot Welder Region": "in_tool",
            "Loading Platform Region": "in_bench",
        }
        converters: List[
            Tuple[
                Optional[FilterType],
                ConverterType,
            ]
        ]
        converters = [
            (
                (lambda m: (m["__table__"] == "triggerregionenterevent")),
                RegionConverter(region_names, default_value=True),
            ),
            (
                (lambda m: (m["__table__"] == "triggerregionexitevent")),
                RegionConverter(region_names, default_value=False),
            ),
            (
                (
                    lambda m: (
                        m["__table__"] == "waypointnotification"
                        and m["achiever"] == "ur10"
                    )
                ),
                cobot_reaches_target,
            ),
            (
                (
                    lambda m: (
                        m["__table__"] == "waypointrequest"
                        and m["label"] == "cobot/next"
                    )
                ),
                cobot_has_target,
            ),
            (
                None,
                DropKey(
                    "id",
                    "collider",
                    "collision_force",
                    "parent_id",
                    "entities",
                ),
            ),
        ]
        # Import trace
        database = DataBase(database_path)
        trace = Trace()
        message_importer = DBMessageImporter(entity_aliases, converters)
        message_importer.import_messages(trace, database)
        # FIXME
        k = ("cobot", "reaches_target")
        for t, v in trace.values[k]:
            if v and t + 1 not in trace.values[k]:
                trace.values[k][t + 1] = False

        # Initialise position defaults
        t = min(next(iter(s))[0] for s in trace.values.values())
        for entity in entity_aliases.values():
            for region in region_names.values():
                position_key = (entity, "position", region)
                if position_key in trace.values:
                    if trace.values[position_key][t] is not None:
                        continue
                else:
                    trace.values[position_key] = TimeSeries()
                trace.values[position_key][t] = False
        return trace, safety_conditions
