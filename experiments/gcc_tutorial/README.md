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
formalise a build configuration format using the `csi` library, and how to
wrap the execution of the build to easily evaluate specific configurations.

### Generating Configuration

The configuration file, if presents, specifies a set of values to overload the 
default ones embedded in the build. It defines the scenario that will play out
in the Digital Twin, and the possible events that will be observed. Unknown 
entries in the configuration file will be ignored. The first step is thus to 
understand what configuration points are available for configuration, and how 
those can be mapped to more convenient objects for generation.

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
configuration. The first step for the `csi` library is to define `dataclasses`
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

The execution of the Digital Twin build under a specific configuration runs the system through a scenario which varies
based on said configuration. The definition of a wrapper around a build eases the evaluation of the system under various
configuration, and the collection and archival of the generated data.

A wrapper should thus take a configuration as an input, run the build with said configuration, and collect the resulting
output for processing. The build considered for the present example takes a single configuration file as an input,
under `StreamingAssets/CSI/gcc-configuration.json`, and produces a log of all messages exchanged during a run, under
`StreamingAssets/CSI/gcc-messages.db`. The log should be cleared before running the build lest messages from prior
executions are included as well.

The `csi` library defines the `Experiment` class to support the definition of small environments to collect experiment
parameters, results, and errors if any. The wrapper needs to define an `execute` method to drive the Digital Twin, based
on a specified build and configuration. Note that each experiment is executed in its own working directory, if paths to
specific resources are required by the wrapper configuration only absolute paths should be considered. The complete
wrapper definition is available under `example/wrapper.py`.

```python
from dataclasses import dataclass
from pathlib import Path
from shutil import copy
from subprocess import run, CalledProcessError

from csi import Experiment, ConfigurationManager
from .configuration import Configuration


@dataclass
class GccRunnerConfiguration:
  build_root: Path
  run_configuration: Configuration


class GccRunner(Experiment):
  configuration: GccRunnerConfiguration
  
  def execute(self) -> None:
    assert self.configuration.build_root.is_absolute()
    # Configure build input/output paths
    assets_path = self.configuration.build_root / "CSI Digital Twin_Data" / "StreamingAssets" / "CSI"
    configuration_path = assets_path / "gcc-configuration.json"
    messages_path = assets_path / "gcc-messages.db"
    executable_path = self.configuration.build_root / "CSI Digital Twin.exe"
    # Prepare build files
    ConfigurationManager(Configuration).save(self.configuration.run_configuration, configuration_path)
    messages_path.unlink(missing_ok=True)
    # Run build
    try:
      run(executable_path, check=True)
    except CalledProcessError as e:
      # Process exception if required
      raise e
    # Save message log
    copy(messages_path, Path("./messages.db"))
```

Defining and running an experiment requires the specification of the root folder where all results will be stored, and
the configuration. In our example, the wrapper configuration needs to provide the location of the build used for the
experiment, and a Digital Twin configuration as specified in the previous section. Calling the `run` method on the
wrapper will result in its execution, with the collection of generated log, errors, and output.

```python
from pathlib import Path
from configuration import Configuration
from wrapper import GccRunnerConfiguration, GccRunner

b = GccRunnerConfiguration(Path("../build/win-gui").absolute(), Configuration())

r = GccRunner("experiments", b)
r.run(retries=3)
```

Note that related experiments should use the same root folder to store related results; multiple experiment instances
using the same root folder will not conflict as each will be assigned a unique id and sub-directory. A `csi.Repository`
pointing to the root folder will then allow for easy access to all experiments sharing the same root, and their results.

The use of the Linux build and the creation of a related Docker container are left as an exercise to the reader.
Consider the `tcx_safety` use case for a reference container and wrapper. The overall approach is similar, with the
volumes exposed by the containers used to save the configuration and collect the output generated by the build. Note
that the paths for the configuration and message log files will have to be adapted. Furthermore, the `gcc_tutorial` use
case does not need the Python IK solver included in `tcx_safety`.

## Monitoring events in the Digital Twin

The wrapper allows the execution of the Digital Twin under controlled conditions, as exposed and defined by the build
configuration. The messages collected during the execution of the build can provide insight on the events that occurred
in the system, and whether specific situations have occurred. The first step is to define which events or metrics need
to be exposed from the system's output. Then we need to define the steps required to generate a trace of such events
over time from the messages collected in the Digital Twin.

### Defining the Situation space

The situation space aims to capture the components of situations in the system, and their domain. Components are the
individual events and metrics extracted from the system. They are used to expressing specific conditions which
occurrence can be monitored. As an example to assess if the robot exceeds its velocity restrictions (a situation), the
velocity of the robot over time (a component) needs to be monitored and extracted from the collected messages. The
situation space is defined through the `csi.situation` module, with `Component` and `Context`.

To assess the safety of the proposed setup, we need to monitor collisions in the environment, that is when a collision
occurs and the force of such collisions:
```python
from csi.situation import Context, Component
from csi.situation import domain_values, domain_threshold_range

class Collision(Context):
  occurs = Component(domain_values({True, False}))
  force = Component(domain_threshold_range(0, 1000, 100, upper=True))
```

We also track when the robot or the operator are moving to understand which might be responsible for the collision:
```python
class Entity(Context):
  is_moving = Component(domain_values({True, False}))
```

The distance measured by the LIDAR may further provide some insight into when the operator was detected if at all:
```python
class Lidar(Context):
  distance = Component()
```

All components and their contexts are brought together to define a single definition of the situation space capturing
the state of collisions, the robot, the operator, and the LIDAR. The full definition is available
under `example/situation.py`:
```python
class Situation:
  robot = Entity()
  operator = Entity()
  lidar = Lidar()
  collision = Collision()
```

The situation definition allows us to define specific conditions to monitor in the system, in particular if any contact
between the robot and the operator occur, and if such contact is hazardous:
```python
from situation import Situation

_S = Situation()

# Any contact between the robot and operator
contact_occurs = _S.collision.occurs.eventually()

# Any hazardous contact between the robot and operator
_COLLISION_FORCE_THRESHOLD = 100
collision_occurs = (
        _S.collision.occurs & _S.collision.force > _COLLISION_FORCE_THRESHOLD
).eventually()
```

We can further rule out if the contact is caused by an operator moving into an immobile robot:
```python
# Any contact due to the operator moving into a stopped robot
operator_collides = (_S.collision.occurs & ~_S.robot.is_moving).eventually()
```

We can also monitor for the correct execution of the controller safety stop, that is the robot should promptly stop if
an obstacle is detected by the LIDAR below the specified distance:

```python
# The robot stops within 250ms when an obstacle gets too close
_SAFETY_STOP_THRESHOLD = 0.75
robot_safety_stops = (
  (_S.lidar.distance < _SAFETY_STOP_THRESHOLD).implies(
    (~_S.robot.is_moving).eventually(0, 0.250)
  )
).always()
```

The full set of monitored conditions is described in `example/monitor.py`.

### Processing the event trace

Open message database, list tables, look at contents of one

Create a trace from messages

Check for condition occurrence from trace