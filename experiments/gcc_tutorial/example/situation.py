from csi.situation import Context, Component
from csi.situation import domain_values, domain_threshold_range


class Collision(Context):
    occurs = Component(domain_values({True, False}))
    force = Component(domain_threshold_range(0, 1000, 100, upper=True))


class Entity(Context):
    is_moving = Component(domain_values({True, False}))


class Lidar(Context):
    distance = Component()


class Situation(Context):
    robot = Entity()
    operator = Entity()
    lidar = Lidar()
    collision = Collision()
