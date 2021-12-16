# ![py-csi-cobotics](assets/csi-cobotics-logo.png?raw=true)

<!-- TODO:ci/pypi/licence badges -->

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
pip install py-csi-cobotics
```

## Usage


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

A run of a Digital Twin instance, allows the user to evaluate the response of the system under a given configuration. It
does require some care to ensure the appropriate files and configuration are generated to execute the run, and to
collect the data produced by the run for further processing. The `Experiment` class aims to ease the process of running
multiple instances of the twin and collecting the resulting traces. Running an `Experiment` generates a record of the
run, with the experiment configuration, status of the run, and a working directory with the generated data. 

An experiment is defined by overriding the `execute` method, introducing all required steps to produce the experimental
data. We recommend the use of relative paths for files generated by the experiment, such as event traces; each run of
the experiment will occur in its separate, dedicated working directory. The experiment configuration is expected to be
compliant with the `csi.ConfigurationManager` as it is serialised into a JSON configuration file as part of the
experiment backup. Experiments stored in the same directory are part of the same `Repository`. A repository provides
convenient access to all experiments, runs, or successful runs thereof.

```python
from csi import Experiment

class SkeletonTwinRunner(Experiment):

    def execute(self) -> None:
        """Run digital twin container with the specified configuration"""
        # Generate configuration file
        # ...
        # Run twin container
        # ...
        # Generate event trace
        # ...
        # Monitor for hazard occurrences
        # ...

e = SkeletonTwinRunner()
e.configuration = SceneConfiguration()
e.run(retries=5)
```

Due to the nature of the twin launcher, configuration and trace files are located in the build folder. Concurrent runs
from the same build might thus result in conflicting experiments, and results being overwritten. It is advised to use
a container to execute the Digital Twin to guarantee isolation, or copy the build folder for each concurrent thread.


### Building a trace of events

Each run of the Digital Twin produces a record of the messages exchanged between the different entities modelled by the
system. This record carries little information regarding the semantic of the messages, their contents, or their
relations to the components required for monitoring situations of interests. It is up to the user to provide some
meaning to said messages for a given twin instance, based on their type, contents, or communication channels.

The `csi.twin` module provides primitives to ease the access to a message record. The `DataBase` type covers the basic
interaction with the message database. `from_table` iterates over all messages in the specified tables, returning each
as a separate object with the same fields as the original message. Note that the message types and contents may vary
based on your twin instance. It is recommended to assess the available messages on a trial run of each instance.

```python
from csi.twin import DataBase, from_table

db = DataBase("/path/to/db")

for m in from_table(db, "movablestatus"):
    print("At time {}, Entity {} is {}moving".format(m.timestamp, m.entity, "not " if not m.is_moving else ""))
```

The `csi.situation` module defines the notion of an event trace to track the values of components' over time, and assess
the occurrence of specific situations. Entries are indexed by their component. Each new value should be recorded with
the instant, as a timestamp, at which the change occurs.

```python
from csi.twin import DataBase, from_table
from csi.situation import Trace

db = DataBase("/path/to/db")
trace = Trace()
P = IndustrialContext()

# Define fixed-value constraint
trace[P.constraints.cobot.velocity.in_bench] = (0.0, 15.0)

# Record operator movement in cell
trace[P.operator.is_moving] = ( 0.0, False)
trace[P.operator.is_moving] = ( 1.0, True)
trace[P.operator.is_moving] = ( 4.0, True)
trace[P.operator.is_moving] = (10.0, False)
```

Situations can be evaluated against a trace to assess whether they occur or not. This is achieved through a monitor,
which operators on a set of situations for evaluation, and extracting relevant properties such as the set of components
used throughout said situations.
```python
from csi.situation import Monitor
# An operator in movement always stops within 5.0 time units
c = (P.operator.is_moving.implies((~P.operator.is_moving).eventually(0, 5.0))).always()
# The operator eventually moves
d = P.operator.is_moving.eventually()

m = Monitor({c, d})

assert m.evaluate(trace)[c] == True
assert m.evaluate(trace)[d] == True
```


### Coverage computation and metrics

The experimental `EventCombinationsRegistry` maintains a record of all combinations of values encountered for a given
set of components. It can process traces to extract such combinations and provide some primitives to compute the
combined components' domain coverage. 

> **WARNING**: This is an experimental feature which is neither pleasant to use nor reliable. Consider the example
> ad-hoc script provided by `experiments/tcx_safety/serialisation_dataset.py` instead.

```python
from csi.situation import EventCombinationsRegistry

e = EventsCombinationsRegistry()

# Define the tracked components' domain (reuse in-situ domain definitions where possible)
e.domain[P.operator.is_moving] = P.operator.is_moving.domain
e.domain[P.operator.velocity] = P.operator.velocity.domain

# Register the events' combinations encountered by a trace
e.register(trace)

print(e.coverage)
```

## Citing

```bibtex
@InProceedings{sassi,
    author="Lesage, Benjamin and Alexander, Rob",
    title="SASSI: Safety Analysis Using Simulation-Based Situation Coverage for Cobot Systems",
    booktitle="Computer Safety, Reliability, and Security (Proceedings of SafeComp)",
    year="2021",
    publisher="Springer International Publishing",
    pages="195--209",
    isbn="978-3-030-83903-1"
}
```

