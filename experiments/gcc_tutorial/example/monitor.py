from situation import Situation

_S = Situation()

_COLLISION_FORCE_THRESHOLD = 100

# Any contact between the robot and operator
contact_occurs = _S.collision.occurs.eventually()

# Any hazardous contact between the robot and operator
collision_occurs = (
    _S.collision.occurs & _S.collision.force > _COLLISION_FORCE_THRESHOLD
).eventually()

# Any contact due to the operator moving into a stopped robot
operator_collides = (_S.collision.occurs & ~_S.robot.is_moving).eventually()

# The robot stops within 250ms when an obstacle gets too close
_SAFETY_STOP_THRESHOLD = 0.75
robot_safety_stops = (
    (_S.lidar.distance < _SAFETY_STOP_THRESHOLD).implies(
        (~_S.robot.is_moving).eventually(0, 0.250)
    )
).always()

monitored_conditions = [
    contact_occurs,
    collision_occurs,
    operator_collides,
    robot_safety_stops,
]
