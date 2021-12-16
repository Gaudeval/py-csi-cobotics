import dataclasses
from datetime import datetime
from pathlib import Path

import mtfl.connective


@dataclasses.dataclass
class Waypoint:
    duration: float = 1.0

    _encoded_fieldnames = {
        "duration": "Waypoint.duration",
    }


@dataclasses.dataclass
class SceneConfiguration:
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


@dataclasses.dataclass
class MonitorConfiguration:
    _logics = {
        "default": mtfl.connective.default,
        "zadeh": mtfl.connective.zadeh,
        "godel": mtfl.connective.godel,
    }

    @property
    def logic(self):
        return self._logics[self.connective]

    connective: str = dataclasses.field(default="default")
    quantitative: bool = dataclasses.field(default=False)


@dataclasses.dataclass
class BuildConfiguration:
    path: Path = dataclasses.field(default_factory=Path)

    @property
    def assets(self) -> Path:
        """Location of simulation assets in build"""
        return self.path / "Unity_Data" / "StreamingAssets" / "CSI"

    @property
    def database(self) -> Path:
        return self.assets / "Databases" / "messages.safety.db"

    @property
    def configuration(self) -> Path:
        return self.assets / "Configuration" / "configuration.json"


@dataclasses.dataclass
class RunnerConfiguration:
    """Digital twin experiment configuration"""

    world: SceneConfiguration
    build: BuildConfiguration
    ltl: MonitorConfiguration = dataclasses.field(default_factory=MonitorConfiguration)
