from pathlib import Path

from csi.twin import DataBase, from_table
from csi.situation import Trace
from situation import Situation


def generate_trace(db_path):
    db = DataBase(db_path)

    t = Trace()
    s = Situation()

    # Robot/Operator moving status
    moving_topics = {
        "/safety/robot/moving": s.robot.is_moving,
        "/safety/operator/moving": s.operator.is_moving,
    }
    for m in from_table(db, "movablestatus"):
        if m.topic in moving_topics:
            t[moving_topics[m.topic]] = (m.timestamp, m.is_moving == 1)

    # Collision occurrences
    for m in from_table(db, "collisionevent"):
        if m.entity_id == "Operator-Tim":
            t[s.collision.occurs] = (m.timestamp, True)
            t[s.collision.force] = (m.timestamp, m.collision_force)
            t[s.collision.occurs] = (m.timestamp + 0.01, False)
            t[s.collision.force] = (m.timestamp + 0.01, 0.0)
    # occurs = Component(domain_values({True, False}))
    # force = Component(domain_threshold_range(0, 1000, 100, upper=True))

    # LIDAR Measurements
    for m in from_table(db, "float32"):
        if m.topic == "/lidar/digital/range":
            t[s.lidar.distance] = (m.timestamp, m.data)

    return t
