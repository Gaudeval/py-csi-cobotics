import json
from pathlib import Path
from typing import Tuple

import numpy

from csi.experiment import Repository, RunStatus, Experiment
from csi.twin.runner import EvaluationConfiguration, BuildRunnerConfiguration
from scenarios.tcx import hazards, unsafe_control_actions, configuration, TcxBuildRunner


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
            run_score = 0
            conditions = ({0}, {0})
            if run.status == RunStatus.COMPLETE:
                with (run.work_path / "hazard-report.json").open() as json_report:
                    report = json.load(json_report)
                    for uid, occurs in report.items():
                        if occurs is None:
                            continue
                        occurs = float(occurs)
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
                [-2.0, 2.0],  # op.x
                [-1.0, 0.0],  # op.y
                [-2.0, 2.0],  # op.z
                [-180, 180],  # op.r
                [0, 2],  # assembly.y
                [-2.0, 0.0],  # rob.x
                [0.0, 0.7],  # rob.y
                [-1.0, 1.0],  # rob.z
                [0, 1],  # ctrl.speed
            ]
        )

    def generate_configuration(self, X):
        def val(i: int):
            return (
                X[i] * (self.var_bound[i][1] - self.var_bound[i][0])
                + self.var_bound[i][0]
            )

        # Prepare configuration
        world = configuration.default()
        world.operator.position.x = val(0)
        world.operator.position.y = val(1)
        world.operator.position.z = val(2)
        world.operator.rotation.y = val(3)
        #
        world.assembly.position.y = [0.84, 0.0, -1.0][int(val(4))]
        #
        world.cobot.position.x = val(5)
        world.cobot.position.y = val(6)
        world.cobot.position.z = val(7)
        #
        world.controller.limit_speed = False if X[8] > 0.5 else True
        return world

    def __call__(self, X):
        world = self.generate_configuration(X)
        # Condition evaluation
        evaluation = EvaluationConfiguration()
        evaluation.logic = self.evaluation_logic
        evaluation.quantitative = self.evaluation_quantitative
        # Prepare experiment
        exp = TcxBuildRunner(
            self.repository.path,
            BuildRunnerConfiguration(world, self.build, evaluation),
        )
        # Load default conditions
        exp.safety_conditions = []
        exp.safety_conditions.extend(hazards)
        exp.safety_conditions.extend(unsafe_control_actions)
        # Run experiment and compute score
        exp.run()
        return self.score_experiment(exp)
