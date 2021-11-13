import shutil
import time
from pathlib import Path
from multiprocessing import Pool


from wrapper.fitness import RunnerFitnessWrapper
import random


def run(seed):
    runs = Path("./runs/")
    w = RunnerFitnessWrapper("./build/", runs, "zadeh", with_features=True)
    random.seed(seed)
    X = [random.random() for _ in range(5)]
    w(X)
    return seed


if __name__ == "__main__":
    runs = Path("./runs/")
    if runs.exists():
        shutil.rmtree(runs)
    #
    random.seed(42)
    time_start = time.time()
    with Pool(processes=10) as pool:
        for i in pool.imap_unordered(run, range(10)):
            print(i)
    time_end = time.time()
    print(f"Runtime: {time_end - time_start}s")
