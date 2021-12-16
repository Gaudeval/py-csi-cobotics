# TCX Use Case

The TCX use case is a case study to assess the safety of an industrial cell. The design of the cell is inspired by the
industrial application of a collaborative robot to support assembly processing. The case study aimed for the evaluation
of situation-based coverage techniques and automated testing techniques, through the CSI:Cobot Digital Twin, to assess
the safety of a system. The evaluation of the use case led to the development of the core concepts defined in the `csi`
package. The following introduces the design and usage of a wrapper around a twin instance modelling the case study.

![Representation of the industrial case study](../../assets/twin_example_cell.png?raw=true)
<!-- ![alt text](https://github.com/[username]/[reponame]/blob/[branch]/image.jpg?raw=true) -->

The case study comprises a human operator, an automated robot arm, and a spot welder. The operator and the arm exchange
an assembly at a shared bench. The arm then proceeds to carry the assembly to the welder for processing, before
returning to the shared bench to deliver the processed assembly. The cell includes a number of sensor to assess the
position of the operator, namely a light barrier at the shared bench, and a LIDAR sensor in the cell to measure the
distance between welder and operator. The twin of the system features a safety controller which aims to minimise the
risk to the operator, by notably interrupting any ongoing processing should the operator enter the cell at an
inopportune time.

## Executing the use case

An example of randomised search linking all components of the framework and using this setup is included
in `./search_ran.py`. The search simply runs a few experiments, generating a random configuration for each. The wrapper
for twin-based experiments includes processing steps to generate a trace of events that occurred in the twin, and assess
the absence or presence of hazardous occurrences in the system. 

The wrapper for the case study relies on Docker to run instances of the digital twin. Docker allows concurrent
executions of same twin build without interferences, and only the required output files are archived.
The `./containers/twin/tcx/`
folder includes the recipe and assets required to build a compatible image. The image, with the expected tag, is built
using the following command from the `Dockerfile` directory:

```shell
docker image build --tag csi-twin:tcx
```

Each experiment ran by the script, outside the standard files, includes a backup of the digital twin output, an SQLite
record of all messages exchanged during the run. The run also includes the processed event trace and a report on
encountered hazards and unsafe control actions. the `./serialisation_dataset.py` script provides for the computation of
some coverage metrics for a repository, a folder of experiments.

## Twin model and configuration

The twin instance included in this release abstracts some aspects of the industrial case study, namely there is no
component exchange between the operator and the arm. The arm autonomously moves from the bench to the welder and
activates the latter when appropriate. The operator follows a pre-determined path through the workspace and into the
cell. The included twin build runs for at most 60 simulated seconds.

The operator path is defined by 5 different waypoints, traversed in order from outside the cell, to the shared bench, to
the cell entrance, to inside the cell, back outside. The wrapper exposes the time spent by the operator at each waypoint
through its configuration (see `wrapper/configuration.py`). By modifying said waiting times, the operator can interfere
with the autonomous process at different key instants. The safety controller deployed in the case study aim to keep the
operator safe in all such cases.

## STPA-produced safety conditions and monitoring

The wrapper monitors for the occurrence of a number of safety-related situations. Those are hazards and unsafe control
actions identified following an STPA safety analysis of the original cell (see `wrapper/safety.py`). Not all hazardous
situations identified by the safety analysis could be formalised due to limitations in the digital twin environment. The
definition of the components used to express those safety-related situations is available in `wrapper/monitor.py`.

## Execution wrapper

The execution wrapper simply runs a Docker container using the specified configuration and image. The resulting message
record is processed to build a trace of events in the system over time, and assess the occurrence of hazards and unsafe
situations (see `wrapper/runner.py`). An additional layer provides for the computation of a fitness metric for each run,
based on how hazard-prone it is. This provides the groundwork for the use of automated search techniques to trigger
safety situations in the system (see `wrapper/fitness.py`).

## Coverage computation

The `wrapper/serialisation_dataset.py` computes the coverage achieved by a set of experiments for different metrics,
based on the triggered situations, the truth value of their individual boolean conditions, or the values observed for
their individual components.
