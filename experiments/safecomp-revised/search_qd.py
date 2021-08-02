import shutil
from pathlib import Path
from qdpy import algorithms, containers, plots

from wrapper.runner import SafecompControllerRunner
from wrapper.fitness import RunnerFitnessWrapper
from scenarios.tcx import hazards, unsafe_control_actions


if __name__ == "__main__":
    runs = Path("./runs/")
    if runs.exists():
        shutil.rmtree(runs)
    #
    w = RunnerFitnessWrapper("./build/", runs, "zadeh", with_features=True)

    H = len([h for h in hazards if h.uid not in SafecompControllerRunner.blacklist])
    U = len(
        [
            u
            for u in unsafe_control_actions
            if u.uid not in SafecompControllerRunner.blacklist
        ]
    )

    grid = containers.Grid(
        shape=(H + 1, U + 1),
        max_items_per_bin=1,
        fitness_domain=(w.score_domain(),),
        features_domain=((0.0, H), (0.0, U)),
    )

    algo = algorithms.RandomSearchMutPolyBounded(
        grid,
        budget=1000,
        batch_size=1,
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
