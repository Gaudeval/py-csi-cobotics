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

An example is available under the `experiments/safecomp-revised`, defining an experimental setup built on top of an industrial case study. The example identifies configurable values in the corresponding twin build, a set of monitors to identify hazard occurrences in the industrial cell, and the processing steps to rebuild the sequence of events occurring in each run.

> **WARNING**: Examples will soon migrate to a separate repository

> **WARNING**: The twin build required to run the experiments is pending release.

### Defining a world configuration

### Monitoring for situations

### Running the twin

### Building a trace of events

### Coverage computation and metrics

## API

## Citing
