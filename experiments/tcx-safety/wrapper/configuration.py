import dataclasses
from datetime import datetime
from pathlib import Path

from csi.configuration import ConfigurationManager
from csi.twin.configuration import BuildConfiguration


@dataclasses.dataclass
class Waypoint:
    duration: float = 1.0

    _encoded_fieldnames = {
        "duration": "Waypoint.duration",
    }


@dataclasses.dataclass
class SafetyWorldConfiguration:
    timestamp: datetime = dataclasses.field(default_factory=lambda: datetime.now())
    version: str = "0.0.0.2"

    wp_start: Waypoint = dataclasses.field(default_factory=Waypoint)
    wp_bench: Waypoint = dataclasses.field(default_factory=Waypoint)
    wp_wait: Waypoint = dataclasses.field(default_factory=Waypoint)
    wp_cell: Waypoint = dataclasses.field(default_factory=Waypoint)
    wp_exit: Waypoint = dataclasses.field(default_factory=Waypoint)

    _encoded_fieldnames = {
        "timestamp": "$Generated",
        "version": "$version",
        "wp_start": "/Operator Controller/Waypoint Bench Entrance/Waypoint",
        "wp_bench": "/Operator Controller/Waypoint Bench/Waypoint",
        "wp_wait": "/Operator Controller/Waypoint Cell Entrance/Waypoint",
        "wp_cell": "/Operator Controller/Waypoint Cell/Waypoint",
        "wp_exit": "/Operator Controller/Waypoint Exit/Waypoint",
    }


class SafetyBuildConfiguration(BuildConfiguration):
    @property
    def database(self) -> Path:
        return self.assets / "Databases" / "messages.safety.db"


if __name__ == "__main__":
    w = SafetyWorldConfiguration()
    w.wp_start.duration = 0.0
    w.wp_bench.duration = 2.0
    w.wp_wait.duration = 4.0
    w.wp_cell.duration = 8.0
    w.wp_exit.duration = 16.0
    print(ConfigurationManager().encode(w))
