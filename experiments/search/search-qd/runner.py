import shutil
from pathlib import Path
from qdpy import algorithms, containers, plots

from scenarios.tcx import hazards, unsafe_control_actions

from experiments.search.fitness import RunnerFitnessWrapper


if __name__ == "__main__":
    runs = Path("./runs/")
    if runs.exists():
        shutil.rmtree(runs)
    #
    w = RunnerFitnessWrapper("../../build_headless/", runs, "zadeh", with_features=True)

    grid = containers.Grid(
        shape=(len(hazards) + 1, len(unsafe_control_actions) + 1),
        max_items_per_bin=1,
        fitness_domain=(w.score_domain(),),
        features_domain=((0.0, len(hazards)), (0.0, len(unsafe_control_actions))),
    )

    algo = algorithms.RandomSearchMutPolyBounded(
        grid,
        budget=2000,
        batch_size=10,
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
