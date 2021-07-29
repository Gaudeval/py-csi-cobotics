import shutil
from pathlib import Path


from wrapper.fitness import RunnerFitnessWrapper
import random


if __name__ == "__main__":
    runs = Path("./runs/")
    if runs.exists():
        shutil.rmtree(runs)
    #
    w = RunnerFitnessWrapper("./build/", runs, "zadeh", with_features=True)

    random.seed(42)
    for i in range(1000):
        X = [random.random() for _ in range(5)]
        w(X)
