import json
from typing import Tuple

import numpy
import shutil
from pathlib import Path

from qdpy import algorithms, containers, benchmarks, plots

from csi.experiment import Repository, Experiment, RunStatus
from csi.twin.runner import BuildRunnerConfiguration
from scenarios.tcx import TcxBuildRunner, hazards, unsafe_control_actions, configuration


class ExperimentWrapper:
    def __init__(self, build="../build/", runs="runs/"):
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
                        if occurs:
                            if any(str(h.uid) == uid for h in hazards):
                                run_score += 10
                                conditions[0].add(self.features[uid])
                            elif any(u.uid == uid for u in unsafe_control_actions):
                                run_score += 1
                                conditions[1].add(self.features[uid])
                return (-run_score,), (max(conditions[0]), max(conditions[1]))

    def generate_configuration(self, X):
        var_bound = numpy.array(
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

        def val(i: int):
            return X[i] * (var_bound[i][1] - var_bound[i][0]) + var_bound[i][0]

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
        # Prepare experiment
        exp = TcxBuildRunner(
            self.repository.path, BuildRunnerConfiguration(world, self.build)
        )
        # Load default conditions
        exp.safety_conditions = []
        exp.safety_conditions.extend(hazards)
        exp.safety_conditions.extend(unsafe_control_actions)
        # Run experiment and compute score
        exp.run()
        return self.score_experiment(exp)


if __name__ == "__main__":
    #
    runs = Path("./runs/")
    if runs.exists():
        shutil.rmtree(runs)
    #
    w = ExperimentWrapper("../build_headless/", runs)

    grid = containers.Grid(
        shape=(len(hazards) + 1, len(unsafe_control_actions) + 1),
        max_items_per_bin=1,
        fitness_domain=((0.0, len(hazards) * 10 + len(unsafe_control_actions)),),
        features_domain=((0.0, len(hazards)), (0.0, len(unsafe_control_actions))),
    )

    algo = algorithms.RandomSearchMutPolyBounded(
        grid,
        budget=1000,
        batch_size=50,
        dimension=9,
        optimisation_task="minimisation",
        ind_domain=(0.0, 1.0),
    )

    logger = algorithms.AlgorithmLogger(algo)

    eval_fn = w

    best = algo.optimise(w)

    print(algo.summary())
    plots.default_plots_grid(logger)
    print("All results in %s" % logger.final_filename)
