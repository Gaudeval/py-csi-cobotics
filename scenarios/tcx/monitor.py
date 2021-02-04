import operator
from functools import reduce
from lenses import bind
from mtl import BOT
from csi.monitor import Alias, Context, Term


class Position(Context):
    in_workspace = Term()
    in_bench = Term()
    in_tool = Term()


class Entity(Context):
    distance = Term()
    position = Position()
    has_assembly = Term()
    is_damaged = Term()
    is_running = Term()
    provides_assembly = Term()
    is_moving = Term()
    velocity = Term()
    has_target = Term()
    reaches_target = Term()


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


class World(Context):
    assembly = Assembly()
    cobot = Entity()
    controller = Controller()
    constraints = Constraints()
    operator = Entity()
    tool = Entity()
    workspace = Workspace()


P = World()

Controller.gets_configured = Alias(
    (~Controller.is_configured) & (Controller.is_configured >> 1)
)

# FIXME Extend to any non-expected entity
Workspace.has_obstruction = P.operator.position.in_workspace

Entity.grabs_assembly = Alias((~Entity.has_assembly) & (Entity.has_assembly >> 1))


Entity.releases_assembly = Alias(Entity.has_assembly & (~Entity.has_assembly >> 1))


Entity.starts = Alias((~Entity.is_running) & (Entity.is_running >> 1))


Entity.acts = Alias(Entity.grabs_assembly | Entity.releases_assembly | Entity.is_moving)


Entities = bind(World).Recur(Entity).collect()


Assembly.is_held = reduce(operator.or_, (e.has_assembly for e in Entities), BOT)


Assembly.is_delivered = P.assembly.is_processed.implies(
    (P.cobot.position.in_bench & (~P.cobot.has_assembly)).eventually()
).always()


Assembly.needs_secured = P.cobot.has_assembly & (~P.cobot.position.in_bench)


Entity.suffers_damage = Alias((~Entity.is_damaged) & (Entity.is_damaged >> 1))
