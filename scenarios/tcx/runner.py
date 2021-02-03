import dataclasses
from pathlib import Path
from typing import Any, Union, Optional, List, Tuple

from traces import TimeSeries

from csi.monitor import Trace, Monitor
from csi.safety import SafetyCondition
from csi.twin import DBMessageImporter
from csi.twin.converter import FilterType, ConverterType, RegionConverter, DropKey
from csi.twin.orm import DataBase
from csi.twin.runner import BuildRunnerConfiguration, BuildRunner
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
class TcxRunnerConfiguration(BuildRunnerConfiguration):
    """Digital twin experiment configuration"""

    world: Any = dataclasses.field(default_factory=WorldData)
    build: Path = dataclasses.field(default_factory=Path)


class TcxBuildRunner(BuildRunner):
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
