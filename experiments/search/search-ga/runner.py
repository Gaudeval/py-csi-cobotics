import shutil
from pathlib import Path
from geneticalgorithm import geneticalgorithm as ga

from experiments.search.fitness import RunnerFitnessWrapper


if __name__ == "__main__":
    #
    runs = Path("runs/")
    if runs.exists():
        shutil.rmtree(runs)
    #
    w = RunnerFitnessWrapper("../../build_headless/", runs, "zadeh", with_features=False)

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
        dimension=len(w.var_bound),
        variable_type_mixed=[["real"] for _ in range(len(w.var_bound))],
        variable_boundaries=[[0., 1.] for _ in range(len(w.var_bound))],
        algorithm_parameters=algorithm_param,
        function_timeout=60,
    )
    model.run()
