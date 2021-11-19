import operator
from enum import IntEnum, unique
from functools import reduce
from lenses import bind
from mtfl import BOT
from csi.situation.components import Context, Alias, Term


@unique
class SafMod(IntEnum):
    PFLIM = 0
    NORMAL = 1
    STOPPED = 2
    SRMST = 3
    SSMON = 4
    HGUID = 5


@unique
class Phase(IntEnum):
    RES = 0
    ACT = 1
    INACT = 2
    MIS = 3
    MIT2 = 4
    MIT = 5
    MIT1 = 6


class Position(Context):
    in_workspace = Term()
    in_bench = Term()
    in_tool = Term()


class Entity(Context):
    distance = Term()
    position = Position()
    is_damaged = Term()
    is_running = Term()
    provides_assembly = Term()
    is_moving = Term()
    velocity = Term()
    has_target = Term()
    reaches_target = Term()


class Grabber(Entity):
    has_assembly = Term()


class ConstraintProximity(Context):
    proximity = Term()
    operation = Term()
    in_bench = Term()
    in_tool = Term()
    in_workspace = Term()
    oob = Term()


class ConstraintCobot(Context):
    velocity = ConstraintProximity()
    distance = ConstraintProximity()


class Constraints(Context):
    cobot = ConstraintCobot()
    tool = ConstraintCobot()


class Assembly(Entity):
    is_processed = Term()
    under_processing = Term()
    is_valid = Term()
    is_orientation_valid = Term()
    is_secured = Term()


class Controller(Context):
    is_configured = Term()


class Workspace(Context):
    pass


class Safety(Context):
    mode = Term()
    hsp = Term()
    hcp = Term()
    hrwp = Term()


class World(Context):
    assembly = Assembly()
    cobot = Grabber()
    controller = Controller()
    constraints = Constraints()
    operator = Grabber()
    tool = Grabber()
    workspace = Workspace()
    lidar = Entity()
    safety = Safety()


# TODO Assess whether Context could have an atoms() method to list all terms/atoms

P = World()

Controller.gets_configured = Alias(
    (~Controller.is_configured) & (Controller.is_configured >> 1)
)

# FIXME Extend to any non-expected entity
Workspace.has_obstruction = P.operator.position.in_workspace

Grabber.grabs_assembly = Alias((~Grabber.has_assembly) & (Grabber.has_assembly >> 1))


Grabber.releases_assembly = Alias(Grabber.has_assembly & (~Grabber.has_assembly >> 1))


Entity.starts = Alias((~Entity.is_running) & (Entity.is_running >> 1))


Grabber.acts = Alias(
    Grabber.grabs_assembly | Grabber.releases_assembly | Grabber.is_moving
)


Entities = bind(World).Recur(Entity).collect()


Grabbers = bind(World).Recur(Grabber).collect()


Assembly.is_held = reduce(operator.or_, (e.has_assembly for e in Grabbers), BOT)


Assembly.is_delivered = (
    (P.cobot.has_assembly & P.assembly.is_processed)
    .implies((P.cobot.position.in_bench & (~P.cobot.has_assembly)).eventually())
    .always()
)


Assembly.needs_secured = P.cobot.has_assembly & (~P.cobot.position.in_bench)


Entity.suffers_damage = Alias((~Entity.is_damaged) & (Entity.is_damaged >> 1))
