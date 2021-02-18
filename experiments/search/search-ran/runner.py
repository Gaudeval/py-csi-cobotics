import shutil
from pathlib import Path


from experiments.search.fitness import RunnerFitnessWrapper
import random


if __name__ == "__main__":
    runs = Path("./runs/")
    if runs.exists():
        shutil.rmtree(runs)
    #
    w = RunnerFitnessWrapper("../../build_headless/", runs, "zadeh", with_features=True)

    random.seed(42)
    for i in range(1000):
        X = [random.random() for _ in range(9)]
        w(X)
