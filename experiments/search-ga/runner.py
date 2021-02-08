import json
import numpy
import shutil
from pathlib import Path
from geneticalgorithm import geneticalgorithm as ga

from csi.configuration import ConfigurationManager
from csi.experiment import Repository, Experiment, Run, RunStatus
from csi.twin.runner import BuildRunnerConfiguration
from scenarios.tcx import TcxBuildRunner, hazards, unsafe_control_actions, configuration


class ExperimentWrapper:
    def __init__(self, build="../build/", runs="runs/"):
        self.build = Path(build).absolute()
        self.repository = Repository(Path(runs))

    def score_experiment(self, experiment: Experiment) -> int:
        score = 0
        for run in experiment.runs:
            run_score = 0
            if run.status == RunStatus.COMPLETE:
                with (run.work_path / "hazard-report.json").open() as json_report:
                    report = json.load(json_report)
                    for uid, occurs in report.items():
                        if occurs:
                            if any(str(h.uid) == uid for h in hazards):
                                run_score += 10
                            elif any(u.uid == uid for u in unsafe_control_actions):
                                run_score += 1
            score = max(score, run_score)
        return -score

    def generate_configuration(self, X):
        # Prepare configuration
        world = configuration.default()
        world.operator.position.x = X[0]
        world.operator.position.y = X[1]
        world.operator.position.z = X[2]
        world.operator.rotation.y = X[3]
        #
        world.assembly.position.y = [0.84, 0.0, -1.0][int(X[4])]
        #
        world.cobot.position.x = X[5]
        world.cobot.position.y = X[6]
        world.cobot.position.z = X[7]
        #
        # world.controller.limit_speed = X[8] > 0
        world.controller.limit_speed = False if X[8] > 0.0 else True
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
    runs = Path("runs/")
    if runs.exists():
        shutil.rmtree(runs)
    #
    w = ExperimentWrapper("../build/", runs)

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
    var_type = numpy.array(
        [
            ["real"],
            ["real"],
            ["real"],
            ["real"],
            ["int"],
            ["real"],
            ["real"],
            ["real"],
            ["int"],
        ]
    )
    algorithm_param = {
        "max_num_iteration": 100,
        "population_size": 10,
        "mutation_probability": 0.1,
        "elit_ratio": 0.01,
        "crossover_probability": 0.5,
        "parents_portion": 0.3,
        "crossover_type": "uniform",
        "max_iteration_without_improv": 20,
    }
    model = ga(
        function=w,
        dimension=len(var_type),
        variable_type_mixed=var_type,
        variable_boundaries=var_bound,
        algorithm_parameters=algorithm_param,
        function_timeout=60,
    )
    model.run()
    #
    best_configuration = w.generate_configuration(model.best_variable)
    print(ConfigurationManager().encode(best_configuration))
    list_experiments = lambda: set(str(e.path) for e in w.repository.experiments)
    population = list_experiments()
    w(model.best_variable)
    best_experiment = next(iter(list_experiments() - population))
    shutil.copytree(best_experiment, "runs/best")
