# GCC Tutorial

The GCC use case puts an operator and a mobile robot in the same enclosed space.
It is a simple setup aimed to highlight the process of setting up the framework.
The objective of the tutorial is to automate experiments using the GCC setup and
to identify an example of a hazardous collisions between the robot and the human
operator.


## Cell Setup

![Overview of the GCC setup](assets/gcc-setup-overview.png?raw=true)

The GCC use case comprises a single operator and a mobile robot with a resting
robot arm on top. The operator moves up and down in the cell, between the two
waypoints identified as `(a)` and `(b)`. The mobile robot similarly follows a
loop through four waypoints, from `(1)` to `(4)`.

The mobile robot aims to avoid collisions with obstacles in its environment. To
that purpose, it is equipped with a front facing LIDAR. The robot controller
initiates an emergency safety stop if an obstacle is detected by the LIDAR. The
mobile robot carries a robot arm, stored in a resting position, which might be
a source of collision. The following image illustrates the configuration of the
robot, with the LIDAR sensor region highlighted.

![Configuration of the GCC robot](assets/gcc-setup-robot.png?raw=true)

Note that the operator does not issue a safety stop; the operator will keep 
moving irrespective of whether its path is obstructed or not. The operator may
thus collide with the robot of its own volition. 

## Digital Twin Build

The tutorial includes two different instances of the Digital Twin with the GCC 
setup under the `build/` folder. Both builds expose the same configuration and
logging file formats:
- `build/win-gui/` is a GUI-enabled build for Windows machines. It provides 
  visual feedback on the behaviour of the system while experimenting with 
  various configurations. The executable for the build is 
  `build/win-gui/CSI Digital Twin.exe`.
- `build/lin-server` is a command line build for Linux machines. It is 
  intended for use in containers for larger scale evaluations. The executable 
  for the build is `build/linux-server/gcc-tutorial.x86_64`

The simulation is set to run for 60 seconds of simulated time, allowing the
operator and the robot to complete multiple loops through their respective
paths. The builds expose a single configuration file to provide some control
over the paths followed by either entity and the behaviour of the robot. All
messages exchanged between entities during the simulation are logged in a
database. Both are stored under the `StreamingAssets/CSI` folder in each build.

### Build configuration

The build configuration is a JSON-based file, located under 
`StreamingAssets/CSI/gcc-configuration.json`. The configuration file is loaded
upon starting a run with the build and overrides a number of predefined 
configuration points. Values missing from the configuration file will use the
defaults embedded in the build. 

If the configuration file is missing upon startup, a default one will be created
including all configuration points with their default values. This is a good
option to understand what are the available configuration points.

### Message log

The message logging database is a SQLite-based file, located under
`StreamingAssets/CSI/gcc-messages.db`. The database captures all messages
generated within the Digital Twin by the various entities, sensors, and
observers. All messages are timestamped using the simulation time, i.e. the
offset of their creation in seconds from the simulation start.

The database is created upon startup if it does not already exist. Messages
will be appended to the database as they are logged. As the database contents
are not cleared on startup, successive runs will log messages into the same
file.

### Observers and messages

All sensors included in the setup send messages capturing their status at 
regular intervals, or upon changes. This is notably the case of the LIDAR and
the range measurements. The builds also include a number of non-diegetic 
sensors, observers which do only exist in the Digital Twin to provide a source 
of ground truth on specific aspects of the system. Two observers capture 
respectively if the operator or robot base are moving, and one observer captures
collision instances between the operator and the robot. Observers raise (and
log) messages upon state changes, that is if any entity stops or starts moving,
or if a collision occurs. Additional messages capture the state of the operator
and the robot as they follow their respective trajectories.

## Building a test harness

A test harness for a Digital Twin build aims to encapsulate the build into a
Python wrapper to ease the execution of multiple instances of the build under
different initial configurations. The harness provides a primitive for the
exploration of the system to assess its behaviour in different scenarios.
This sections looks at how to define such a harness, to understand how to
formalise a build configuration format using the `csi` package, and how to
wrap the execution of the build to easily evaluate specific configurations.

### Generating Configuration

The configuration file, if presents, specifies a set of values to overload the 
default ones embedded in the build. Unknown entries will be ignored. The first
step is thus to understand what configuration points are available for 
configuration, and how those can be mapped to more convenient objects for
generation.

Open the folder for the build corresponding to your target platform, and remove
the configuration file if any (under 
`StreamingAssets/CSI/gcc-configuration.json`). Run the build once to generate 
the default configuration file, with all configuration points, and open it.
The configuration file contains entries for different types of objects. Each
entry is tagged with a unique identifier in the system, and each value with a
unique property name for that object. As an example, the following entry is
the configuration for Waypoint 2 of the mobile robot (`iAM-R`) trajectory:
```json
{
  "/iAM-R Trajectory/Waypoint 2/Waypoint": {
    "Waypoint.isTemporalConstraint": true,
    "Waypoint.duration": 5.0,
    "Waypoint.isPositionConstraint": true,
    "Waypoint.positionTolerance": 0.01,
    "Waypoint.isRotationConstraint": true,
    "Waypoint.rotationTolerance": 0.01,
    "Waypoint.islocal": false,
    "Waypoint.Label": "Waypoint 2"
  }
}
```

Different objects of the same types are exposed through configuration. They 
expose the same properties for each type: entities (e.g. `Operator/Operator`),
waypoints, the LIDAR sensor range 
(`/iAM-R/mir100/LaserSentinel/SensorRange/LidarSensorRange`), and the robot
controller (`GccIamrController.frontRangeStopThreshold`). We ignore entities'
configuration, as it mostly pertains to internals of the Digital Twin, and
logging information.

Let us first consider the configuration of a waypoint. Three pairs of fields 
capture the constraint defined by the waypoint and its configuration, i.e. 
should the entity reach the waypoint position, rotation, or waiting time. Note
that the waypoint position and rotation themselves are not exposed for
configuration. The first step for the `csi` module is to define `dataclasses`
capturing the required configuration points. The `_encoded_fieldnames`
dictionary defines the mapping between names in Python and the configuration
file.

```python
from dataclasses import dataclass

@dataclass
class Waypoint:
    is_temporal_constraint: bool = True
    duration: float = 1.

    _encoded_fieldnames = {
      "is_temporal_constraint": "Waypoint.isTemporalConstraint",
      "duration": "Waypoint.duration",
    }
```

The configuration file includes metadata to specify a version number and 
timestamp. Those can be similarly specified using a `dataclass`. All waypoints
in the included build are configured at the root of the file, at the same level
as the metadata. They can be defined using the `Waypoint` class. The 
`_encoded_fieldnames` provides the same role of mapping names between Python and
the configuration file. The following configuration class captures all the
operator's waypoints configuration:
```python
from dataclasses import dataclass, field
from datetime import datetime

@dataclass
class Waypoint:
  pass

@dataclass
class Configuration:
    operator_wp_a: Waypoint = field(default_factory=Waypoint)
    operator_wp_b: Waypoint = field(default_factory=Waypoint)

    timestamp: datetime = field(default_factory=lambda: datetime.now())
    version: str = "0.0.0.2"
    
    _encoded_fieldnames = {
      "timestamp": "$Generated",
      "version": "$version",
      "operator_wp_a": "/Operator Trajectory/Waypoint a/Waypoint",
      "operator_wp_b": "/Operator Trajectory/Waypoint b/Waypoint",
    }
```

The resulting `Configuration` class can be used to override specific
configuration points, and generate a corresponding twin-compatible JSON file
through the `csi.ConfigurationManager`:
```python
from csi import ConfigurationManager

class Configuration:
  pass

# Create and configure a specific instance
c = Configuration()
c.operator_wp_b.duration = 5.0

# Generate the JSON object corresponding to the configuration
print(ConfigurationManager(Configuration).encode(c))

# Save the configuration in the specified JSON file 
ConfigurationManager(Configuration).save(c, "path/to/configuration.json")
```

A more complete example of a configuration wrapper for the included build,
covering sensor and controller configuration, is available under
`example/configuration.py`


### Running the Digital Twin

Windows only.

Linux build, and the creation of a Docker container, left as an exercise to the
reader. See xxx for example.

## Monitoring events in the Digital Twin

### Defining the Situation space

Components + domain

Monitor + Situations of interest

### Processing the event trace

