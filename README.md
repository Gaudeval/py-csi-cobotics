> **WARNING**: The package is currently undergoing significant refactoring in preparation for a clean release. Things will break, but they shall be repaired soon after.

# py-csi-cobotics

TODO: logo

TODO:ci/pypi/licence badges

A Python framework for controlling and processing experiments built upon the CSI:Cobot Digital Twin.

## Features

- Generate twin configuration files from Python dataclasses
- Collect and process messages generated during a twin run
- Define temporal logic monitors to check for specific situations in a run
- Wrap experiments to support failure, retries, and archiving results
- Compute coverage of the observed situations across multiple runs

## Installation

There is an experimental release of the library available on `test.pypi.org`:
```shell
pip install -i https://test.pypi.org/simple/ py-csi-cobotics
```

## Usage

> **WARNING**: Examples will soon migrate to a separate repository
> **WARNING**: The twin build required to run the experiments is pending release.

The CSI cobotics framework aim to control an instance of the CSI:Cobot Digital Twin, and process the resulting outputs
to identify occurrences of specific events or situations. Through the example of an industrial use case, we introduce
the required steps, from exposing the configuration points of the twin instance, to collecting a trace of events in the
system, and to identifying hazardous situations. Note that the process can be applied in parts for different kind of
analyses.

This documentation will refer to the example available under the `experiments/tcx_safety`, defining an experimental
setup built on top of an industrial case study. The case study comprises a human operator, an automated robotic arm, and
a spot welder. The operator and the arm interact at a shared bench, the arm then moves to a spot welder to process a
component before returning to the bench. A safety controller ensures that interferences from the operator, reaching at
the shared bench or entering the cell, do not result in hazardous situations.

![Representation of the industrial case study](assets/twin_example_cell.png?raw=true)
<!-- ![alt text](https://github.com/[username]/[reponame]/blob/[branch]/image.jpg?raw=true) -->

The operator is set to follow a pre-established path through 5 different, ordered waypoints. The experiment exposes for
configuration the time spent by the operator at each waypoint, allowing for operator interferences at various stage of
the welding process. An example of randomised search linking all components of the framework and using this setup is
included in `experiments/tcx_safety/search_ran.py`.

### Defining a world configuration

The first step in interacting with a CSI: Cobot Digital Twin instance is providing entry points to configure the twin
execution. The `ConfigurationManager` aims to convert Python structures capturing the configuration of the system, and
the JSON-based configuration format of the twin. It supports a variety of structures (`dataclasses.dataclass`
types, `csi.configuration.JsonSerializable` implementations, JSON objects) as inputs. Nesting and mixing structure types
is supported and the value of encoded fields will itself be encoded by the `ConfigurationManager`. Additional meta-data
might be required to map input fields' names into their twin counterparts.

Consider a twin instance exposing two waypoints which duration property captures how long the operator should wait at
the waypoint. The scene configuration is declared as a hierarchy of `dataclass`:

```python
import dataclasses

# Configuration hierarchy declaration
@dataclasses.dataclass
class Waypoint:
    duration: float = 1.0


@dataclasses.dataclass
class SceneConfiguration:
    # twin meta-data
    timestamp: datetime = dataclasses.field(default_factory=lambda: datetime.now())
    version: str = "0.0.0.2"
    # scene configuration
    wp_start: Waypoint = dataclasses.field(default_factory=Waypoint)
    wp_exit: Waypoint = dataclasses.field(default_factory=Waypoint)

    # Declare mapping between Python field names and their configuration counterpart
    _encoded_fieldnames = {
        "timestamp": "$Generated",
        "version": "$version",
        "wp_start": "/Operator Controller/Waypoint Bench Entrance/Waypoint",
        "wp_exit": "/Operator Controller/Waypoint Exit/Waypoint",
    }
```

A configuration for the twin can be initialised and manipulated as a Python object:
```python
configuration = SceneConfiguration()
configuration.wp_start.duration = 5.
configuration.wp_exit.duration = 10.
```

The `ConfigurationManager` can then generate a twin-compliant configuration file for a specific configuration instance
of the configuration:
```python
from csi import ConfigurationManager
ConfigurationManager().save(configuration, "/csi/build/configuration.json")
```

The `ConfigurationManager` can further load serialised configuration into a specific configuration type declaration:
```python
from csi import ConfigurationManager
configuration = ConfigurationManager(SceneConfiguration).load("/csi/build/configuration.json")
```

The resulting JSON file includes all the required meta-data for use by the twin, and the fields named as instructed.
Values omitted from the JSON configuration file, such as the waypoint positions, will use the defaults built into the
twin instance.

```json
{
  "$Generated": "12/12/2021 12:12:12",
  "$version": "0.0.0.2",
  "/Operator Controller/Waypoint Bench Entrance/Waypoint": {
    "Waypoint.duration": 5.0
  },
  "/Operator Controller/Waypoint Exit/Waypoint": {
    "Waypoint.duration": 10.0
  }
}
```

#### Location of the twin configuration file

The configuration file for a twin instance or build is located in Unity's streaming assets folder. Assuming the twin
instance is located under the `/build` folder, the configuration file defaults to
`/build/unity_Data/StreamingAssets/CSI/Configuration/configuration.json`. Runs of a same build copy will rely on the
same configuration file, and runs under different configurations should either be performed in sequence or by first
duplicating the build copy for each configuration file.

#### Configuration field renaming

By default, the `ConfigurationManager` uses the same name field name in Python and in the JSON configuration. The twin
configuration file format uses long hierarchical names to uniquely identify configurable items in a specific instance,
names which might not follow the Python naming conventions. The `ConfigurationManager` thus looks for the
the `_encoded_fieldnames: dict[str, str]` metadata dictionary, if it exists, to indicate how specific fields should be
mapped or renamed from Python to JSON. `_encoded_fieldnames` is expected to be declared as a class attribute for
configuration-encoding classes.

As an example, consider the following `Waypoint` declaration:

```python
import dataclasses

@dataclasses.dataclass
class Vector3D:
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0

@dataclasses.dataclass
class Waypoint:
    duration: float = 1.0
    position: Vector3D = dataclasses.field(default_factory=Vector3D)

    _encoded_fieldnames = {
        "position": "Entity.position",
        "duration": "Waypoint.duration",
    }
    
# A Waypoint will be encoded as:
# {
#    "Entity.position": {
#        "x": 0.0,
#        "y": 0.0,
#        "z": 0.0
#    },
#    "Waypoint.duration": 1.0
# }
```

#### Configuration through dataclasses

The `ConfigurationManager` supports the generation of a JSON object from
a [Data Class](https://docs.python.org/3/library/dataclasses.html) instance. Each field declared in the `dataclass` will
be itself converted into an appropriate JSON value. The name of the encoded field defaults to the `dataclass` field
name, unless specified otherwise through the supported metadata.

```python
import dataclasses


@dataclasses.dataclass
class Vector3D:
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0


@dataclasses.dataclass
class Entity:
    position: Vector3D = dataclasses.field(default_factory=Vector3D)
    rotation: Vector3D = dataclasses.field(default_factory=Vector3D)

    _encoded_fieldnames = {
        "position": "Entity.position",
        "rotation": "Entity.eulerAngles",
    }


@dataclasses.dataclass
class Operator(Entity):
    height: float = dataclasses.field(default=1.75)

    _encoded_fieldnames = {
        "height": "Operator.height",
        "position": "Entity.position",
        "rotation": "Entity.eulerAngles",
    }


@dataclasses.dataclass
class WorldData:
    operator: Operator = dataclasses.field(default_factory=Operator)
    robot: Entity = dataclasses.field(default_factory=Entity)

    _encoded_fieldnames = {
        "operator": "/Operators/Tim/Operator",
        "robot": "/ur10/UR10",
    }
```

#### Configuration through JsonSerializable

The `ConfigurationManager` supports the generation of JSON value from `JsonSerializable` objects, implementing
the `to_json` and `from_json` primitives. Those can further rely on the `ConfigurationManager` methods to encode their
fields. 

```python
from csi import ConfigurationManager
from csi.configuration import JsonSerializable


class ComplexFloat(JsonSerializable):
    _value: float
    
    def to_json(self):
        return self._value
    
    @classmethod
    def from_json(cls, obj):
        c = ComplexFloat()
        c._value = obj
        return c

    
class ComplexWaypoint(JsonSerializable):
    duration: ComplexFloat
    
    def to_json(self):
        return {
            "d": ConfigurationManager().encode(self.duration),
        }
    
    @classmethod
    def from_json(cls, obj):
        w = ComplexWaypoint()
        w.duration = ConfigurationManager(ComplexFloat).decode(obj["d"])
        return w
```


### Monitoring for situations

Defining the situations domain (hierarchy and terms' domains)
Defining the situations

### Running the twin

### Building a trace of events

### Coverage computation and metrics

## API

## Citing
