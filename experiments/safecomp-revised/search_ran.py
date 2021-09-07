import shutil
import time
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
    time_start = time.time()
    for i in range(1000):
        X = [random.random() for _ in range(5)]
        w(X)
    time_end = time.time()
    print(f"Runtime: {time_end - time_start}s")
