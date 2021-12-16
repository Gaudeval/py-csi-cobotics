from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class Waypoint:
    is_temporal_constraint: bool = True
    duration: float = 1.0
    is_position_constraint: bool = True
    position_tolerance: float = 0.01
    is_rotation_constraint: bool = True
    rotation_tolerance: float = 0.01

    _encoded_fieldnames = {
        "is_temporal_constraint": "Waypoint.isTemporalConstraint",
        "duration": "Waypoint.duration",
        "is_position_constraint": "Waypoint.isPositionConstraint",
        "position_tolerance": "Waypoint.positionTolerance",
        "is_rotation_constraint": "Waypoint.isRotationConstraint",
        "rotation_tolerance": "Waypoint.rotationTolerance",
    }


@dataclass
class Controller:
    threshold_front_range: float = 0.75

    _encoded_fieldnames = {
        "threshold_front_range": "GccIamrController.frontRangeStopThreshold",
    }


@dataclass
class LidarRange:
    range: float
    fov: float
    resolution: int

    def __init__(self, range=1.0, fov=160.0, resolution=64):
        assert range > 0.0
        assert fov < 180.0
        assert resolution > 32
        self.range = range
        self.fov = fov
        self.resolution = resolution

    _encoded_fieldnames = {
        "fov": "LidarSensorRange.fieldOfView",
        "range": "LidarSensorRange.range",
        "resolution": "LidarSensorRange.resolution",
    }


@dataclass
class Configuration:
    operator_wp_a: Waypoint = field(default_factory=Waypoint)
    operator_wp_b: Waypoint = field(default_factory=Waypoint)
    robot_wp_1: Waypoint = field(default_factory=Waypoint)
    robot_wp_2: Waypoint = field(default_factory=Waypoint)
    robot_wp_3: Waypoint = field(default_factory=Waypoint)
    robot_wp_4: Waypoint = field(default_factory=Waypoint)

    robot_controller: Controller = field(default_factory=Controller)
    lidar_front: LidarRange = field(default_factory=LidarRange)

    timestamp: datetime = field(default_factory=lambda: datetime.now())
    version: str = "0.0.0.2"

    _encoded_fieldnames = {
        "timestamp": "$Generated",
        "version": "$version",
        "operator_wp_a": "/Operator Trajectory/Waypoint a/Waypoint",
        "operator_wp_b": "/Operator Trajectory/Waypoint b/Waypoint",
        "robot_wp_1": "/iAM-R Trajectory/Waypoint 1/Waypoint",
        "robot_wp_2": "/iAM-R Trajectory/Waypoint 2/Waypoint",
        "robot_wp_3": "/iAM-R Trajectory/Waypoint 3/Waypoint",
        "robot_wp_4": "/iAM-R Trajectory/Waypoint 4/Waypoint",
        "lidar_front": "/iAM-R/mir100/LaserSentinel/SensorRange/LidarSensorRange",
        "robot_controller": "/iAM-R Controller/GccIamrController",
    }
