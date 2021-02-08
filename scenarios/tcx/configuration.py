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
class Entity:
    position: Vector3D = dataclasses.field(default_factory=Vector3D)
    rotation: Vector3D = dataclasses.field(default_factory=Vector3D)

    _encoded_fieldnames = {
        "position": "Entity.position",
        "rotation": "Entity.eulerAngles",
    }


@dataclasses.dataclass
class Controller:
    limit_speed: bool = dataclasses.field(default=True)

    _encoded_fieldnames = {"limit_speed": "UrdfController.useLimits"}


@dataclasses.dataclass
class Operator(Entity):
    height: float = dataclasses.field(default=1.75)

    _encoded_fieldnames = {
        "height": "Operator.height",
        "position": "Entity.position",
        "rotation": "Entity.eulerAngles",
    }


@dataclasses.dataclass
class WorldData:
    timestamp: datetime.datetime = dataclasses.field(
        default_factory=lambda: datetime.datetime.now()
    )
    operator: Operator = dataclasses.field(default_factory=Operator)
    cobot: Entity = dataclasses.field(default_factory=Entity)
    tool: Entity = dataclasses.field(default_factory=Entity)
    assembly: Entity = dataclasses.field(default_factory=Entity)
    controller: Controller = dataclasses.field(default_factory=Controller)
    version: str = "0.0.0.2"

    _encoded_fieldnames = {
        "controller": "/ur10/MultiJointPositionController",
        "operator": "/Operators/Tim/Operator",
        "cobot": "/ur10/UR10",
        "tool": "/Tecconex Cell/Spot Welder Assembly/StaticEntity",
        "assembly": "/Tecconex Cell/TT7302-mandrel/StaticEntity",
        "timestamp": "$Generated",
        "version": "$version",
    }


def default() -> WorldData:
    world = WorldData()
    #
    world.operator.position.x = 1.5  # U/D
    world.operator.position.y = 0  # Height
    world.operator.position.z = 0  # L/R
    #
    world.operator.rotation.x = 0  # Back/Front
    world.operator.rotation.y = -90  # Direction facing
    world.operator.rotation.z = 0  # Left / Right
    #
    world.operator.height = 1.75
    #
    world.cobot.position.x = -0.908
    world.cobot.position.y = 0.778844
    world.cobot.position.z = 0.7
    #
    world.cobot.rotation.x = 0.0
    world.cobot.rotation.y = 180.0
    world.cobot.rotation.z = 0.0
    #
    world.tool.position.x = -2.097
    world.tool.position.y = 0.0
    world.tool.position.z = 0.0
    #
    world.assembly.position.x = -0.105
    world.assembly.position.y = 0.0  # 0.84
    world.assembly.position.z = 0.0
    #
    world.assembly.rotation.x = 0.0
    world.assembly.rotation.y = 0.0
    world.assembly.rotation.z = 90.0
    #
    world.controller.limit_speed = True
    return world
