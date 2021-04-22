import dataclasses
from pathlib import Path
from typing import Any

import mtl.connective


@dataclasses.dataclass
class BuildConfiguration:
    path: Path = dataclasses.field(default_factory=Path)

    @property
    def assets(self) -> Path:
        """Location of simulation assets in build"""
        return self.path / "Unity_Data" / "StreamingAssets" / "CSI"

    @property
    def database(self) -> Path:
        return self.assets / "Databases" / "database.db"

    @property
    def configuration(self) -> Path:
        return self.assets / "Configuration" / "configuration.json"

    @property
    def screenshots(self) -> Path:
        return self.assets / "Screenshots"


@dataclasses.dataclass
class TemporalLogicConfiguration:
    _logics = {
        "default": mtl.connective.default,
        "zadeh": mtl.connective.zadeh,
        "godel": mtl.connective.godel,
    }

    @property
    def logic(self):
        return self._logics[self.connective]

    connective: str = dataclasses.field(default="default")
    quantitative: bool = dataclasses.field(default=False)


@dataclasses.dataclass
class DigitalTwinConfiguration:
    """Digital twin base experiment configuration"""

    world: Any
    build: BuildConfiguration
    ltl: TemporalLogicConfiguration = dataclasses.field(
        default_factory=TemporalLogicConfiguration
    )
