import dataclasses
from pathlib import Path
from typing import Any

import mtl.connective


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
    build: Path = dataclasses.field(default_factory=Path)
    ltl: TemporalLogicConfiguration = dataclasses.field(
        default_factory=TemporalLogicConfiguration
    )
