import dataclasses
import datetime
import enum


class TwinMode(enum.IntEnum):
    DISABLED = 0
    EMULATED = 1
    NETWORKED = 2


@dataclasses.dataclass
class Vector3D:
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0


@dataclasses.dataclass
class Operator:
    position: Vector3D = dataclasses.field(default_factory=Vector3D)

    _encoded_fieldnames = {"position": "Entity.position"}


@dataclasses.dataclass
class WorldData:
    timestamp: datetime.datetime = dataclasses.field(
        default_factory=lambda: datetime.datetime.now()
    )
    operator: Operator = dataclasses.field(default_factory=Operator)
    version: str = "0.0.0.1"

    _encoded_fieldnames = {
        "operator": "Tim-Operator-0",
        "timestamp": "$Generated",
        "version": "$version",
    }
