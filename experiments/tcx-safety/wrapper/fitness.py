import json
from pathlib import Path
from typing import Tuple

import numpy

from csi.experiment import Repository, RunStatus, Experiment
from csi.twin.configuration import TemporalLogicConfiguration
from csi.twin.runner import DigitalTwinConfiguration
from .safety import hazards, unsafe_control_actions

from .configuration import SafetyWorldConfiguration, SafetyBuildConfiguration
from .runner import SafecompControllerRunner


class RunnerFitnessWrapper:
    def __init__(
        self, build="../build/", runs="runs/", logic="default", with_features=True
    ):
        self.build = Path(build).absolute()
        self.repository = Repository(Path(runs))
        self.features = {}
        self.features.update(
            {str(h.uid): i for i, h in enumerate(sorted(hazards), start=1)}
        )
        self.features.update(
            {
                str(h.uid): i
                for i, h in enumerate(sorted(unsafe_control_actions), start=1)
            }
        )
        self.evaluation_logic = logic
        self.evaluation_quantitative = True
        self.retrieve_features = with_features

    @staticmethod
    def score_domain():
        return (0.0, sum(10 for _ in hazards) + sum(1 for _ in unsafe_control_actions))

    def score_experiment(
        self, experiment: Experiment
    ) -> Tuple[Tuple[int], Tuple[int, int]]:
        for run in experiment.runs:
            if run.status == RunStatus.COMPLETE:
                return self.score_report(run.work_path / "hazard-report.json")

    def score_report(self, report_path):
        run_score = 0
        conditions = ({0}, {0})
        report = json.load(Path(report_path).open())
        for uid, occurs in report.items():
            # Constraint occurs domain to [0, 1]
            if occurs is None:
                continue
            occurs = float(occurs)
            occurs = min(1, max(0, occurs))
            # Weigh contribution by safety condition type
            is_hazard = any(h.uid == uid for h in hazards)
            is_uca = any(u.uid == uid for u in unsafe_control_actions)
            if is_hazard:
                run_score += occurs * 10
                if occurs > 0.0:
                    conditions[0].add(self.features[uid])
            if is_uca:
                run_score += occurs * 1
                if occurs > 0.0:
                    conditions[1].add(self.features[uid])

        if self.retrieve_features:
            return (run_score,), (max(conditions[0]), max(conditions[1]))
        else:
            return -run_score

    @property
    def var_bound(self):
        return numpy.array(
            [
                [0.0, 30.0],  # wp_start.duration
                [0.0, 30.0],  # wp_bench.duration
                [0.0, 30.0],  # wp_wait.duration
                [0.0, 30.0],  # wp_cell.duration
                [0.0, 30.0],  # wp_exit.duration
            ]
        )

    def generate_configuration(self, X):
        def val(i: int):
            return (
                X[i] * (self.var_bound[i][1] - self.var_bound[i][0])
                + self.var_bound[i][0]
            )

        # Prepare configuration
        world = SafetyWorldConfiguration()
        world.wp_start.duration = val(0)
        world.wp_bench.duration = val(1)
        world.wp_wait.duration = val(2)
        world.wp_cell.duration = val(3)
        world.wp_exit.duration = val(4)
        return world

    def __call__(self, X):
        world = self.generate_configuration(X)
        # Condition evaluation
        evaluation = TemporalLogicConfiguration()
        evaluation.connective = self.evaluation_logic
        evaluation.quantitative = self.evaluation_quantitative
        # Build configuration
        b = SafetyBuildConfiguration(self.build)
        # Prepare experiment
        exp = SafecompControllerRunner(
            self.repository.path,
            DigitalTwinConfiguration(world, b, evaluation),
        )
        # Run experiment and compute score
        exp.run()
        return self.score_experiment(exp)
