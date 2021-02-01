from csi.monitor import Context, Term


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
    grabs_assembly = Term()
    releases_assembly = Term()
    is_moving = Term()
    velocity = Term()


class ConstraintProximity(Context):
    proximity = Term()
    operation = Term()


class ConstraintCobot(Context):
    velocity = ConstraintProximity()
    distance = ConstraintProximity()


class Constraints(Context):
    cobot = ConstraintCobot()
    tool = ConstraintCobot()


class Assembly(Entity):
    is_held = Term()
    is_processed = Term()
    under_processing = Term()
    is_valid = Term()
    is_orientation_valid = Term()
    is_secured = Term()


class Controller(Context):
    is_configured = Term()


class Workspace(Context):
    has_obstruction = Term()


class World(Context):
    assembly = Assembly()
    cobot = Entity()
    controller = Controller()
    constraints = Constraints()
    operator = Entity()
    tool = Entity()
    workspace = Workspace()


P = World()
