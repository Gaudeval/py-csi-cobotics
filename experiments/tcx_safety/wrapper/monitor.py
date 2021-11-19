import operator
from enum import IntEnum, unique
from functools import reduce
from lenses import bind
from mtfl import BOT
from csi.situation.components import Context, Alias, Term
from csi.situation.domain import domain_values, domain_threshold_range


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
    in_workspace = Term(domain_values({True, False}))
    in_bench = Term(domain_values({True, False}))
    in_tool = Term(domain_values({True, False}))


class Entity(Context):
    distance = Term(domain_threshold_range(0.0, 4.0, 0.25, upper=True))
    position = Position()
    is_damaged = Term(domain_values({True, False}))
    is_running = Term(domain_values({True, False}))
    provides_assembly = Term(domain_values({True, False}))
    is_moving = Term(domain_values({True, False}))
    velocity = Term(domain_threshold_range(0.0, 16.0, 0.25, upper=True))
    has_target = Term(domain_values({True, False}))
    reaches_target = Term(domain_values({True, False}))


class Grabber(Entity):
    has_assembly = Term(domain_values({True, False}))


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
    is_processed = Term(domain_values({True, False}))
    under_processing = Term(domain_values({True, False}))
    is_valid = Term(domain_values({True, False}))
    is_orientation_valid = Term(domain_values({True, False}))
    is_secured = Term(domain_values({True, False}))


class Controller(Context):
    is_configured = Term(domain_values({True, False}))


class Workspace(Context):
    pass


class Safety(Context):
    mode = Term(domain_values(list(SafMod)))
    hsp = Term(domain_values(list(Phase)))
    hcp = Term(domain_values(list(Phase)))
    hrwp = Term(domain_values(list(Phase)))


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
