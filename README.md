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


### Defining situations of interest

Monitoring encapsulates all steps required to define the events and metrics exposed by a twin instance, and the
definition of situations to be monitored in the environment. This is the core of the `csi.situation` module. Situations
capture states of interest in the system, and they can enforce requirements to be maintained or hazardous configurations
to be avoided over its lifetime. They are concretely defined as temporal logic predicates, through
the [py-metric-temporal-logic](https://github.com/mvcisback/py-metric-temporal-logic) library, combining components
using boolean or temporal operators. As an example the twin might expose the velocity of different autonomous agents
throughout the simulation, and their proximity to various obstacles. Specific monitors can be defined to ensure that
agents in proximity to each other do slow down to reduce the likelihood of accidents, and that they never exceed their
speed limit.

#### Defining the components of the system

Components are the building blocks of a situation. They represent individual metrics which evolution over time might
satisfy a specific situation, a state of interest in the system. Related components are defined under the same context,
and contexts themselves may be nested in other contexts. Components of a system are thus defined as a type hierarchy
built on top of the `Component` and `Context` base types.

```python
from csi.situation import Context, Component


class Position(Context):
    in_cell = Component()
    in_bench = Component()
    in_tool = Component()


class Entity(Context):
    position = Position()
    is_moving = Component()
    velocity = Component()


class Welder(Entity):
    is_active = Component()


class Cell(Context):
    welder = Welder()
    robot = Entity()


class IndustrialContext(Context):
    operator = Entity()
    cell = Cell()
```

#### Formalising situations

Situations capture states of interest in the system, requirements that should be maintained across its lifecycles,
occurrences which should be avoided, or combinations of events that need to be encountered during testing. Situations
are formalised as temporal logic predicates which condition components through boolean and temporal operators, using
the `mtl` library. `Component` can be combined into complex boolean or temporal operators using the syntax proposed in
[py-metric-temporal-logic](https://github.com/mvcisback/py-metric-temporal-logic).

```python
i = IndustrialContext()

# Hazard: the operator is in the cell while the welder is active
h = ((i.operator.position.in_cell | i.operator.position.in_tool) & i.cell.welder.is_active).eventually()

# Req: only an active robot at the tool can trigger the welder
r = i.cell.welder.is_active.implies(i.cell.robot.position.in_tool)

# Check: the welder never moves
c = (~i.cell.welder.is_moving).always()
```

In some instances, it might be useful to define a situation for any instance of a context, irrespective of how it can be
nested or reused in other contexts. The purpose of the `Alias` primitive is to make such self-referencing definitions
more convenient.

```python
from csi.situation import Alias

Position.reaches_tool = Alias((~Position.in_tool) & (Position.in_tool >> 1))
# Automatically defines the following:
# - i.operator.position.reaches_tool
# - i.cell.robot.reaches_tool
# - i.cell.welder.reaches_tool

Welder.check_setup = Alias(~Welder.is_moving & Welder.position.in_tool)
assert i.cell.welder.check_setup == (~i.cell.welder.is_moving & i.cell.position.in_tool)
```

#### Defining components' domain for coverage

A domain captures the possible values or ranges thereof for a component. By defining the domain of a component, one can
assess the portion of said domain covered by a set of observations, and whether additional observations might be of
interest. The notion of coverage extends to sets of components and their domains; covering a set of components requires
covering all value combinations of their domains. A domain can be defined for a component upon declaration. A domain
only requires to define a conversion operation, from an observed value to a domain one, capturing in which value/range
thereof the observation fits, and a length if applicable. The framework offers a number of primitives to define common
domains:

```python
from csi.situation import domain_values, domain_identity, domain_threshold_range
from csi.situation import Context, Component


class Entity(Context):
    # Domain values, exact set of values of interest
    is_moving = Component(domain_values({True, False}))
    
    # Identity domain, unbounded, all encountered values are recorded
    status = Component(domain_identity())
    
    # Range domain, the interval [0; 16) is divided into equal-length (0.25) intervals
    velocity = Component(domain_threshold_range(0.0, 16.0, 0.25, upper=True))
```

Note that the domain is mostly used in the computation of coverage metrics for one or more event traces. Event traces
are collected by processing the outputs of a twin instance and discussed in the following sections.

### Running the twin



Experiment definition
Gotcha of concurrent runs from same build folder
Getting data in
Retrieving outputs
Processing outputs


### Building a trace of events

### Coverage computation and metrics

## API

## Citing
