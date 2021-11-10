import random
import shutil
from pathlib import Path

from csi.twin.configuration import DigitalTwinConfiguration, TemporalLogicConfiguration
from wrapper.configuration import SafetyWorldConfiguration, SafetyBuildConfiguration
from wrapper.runner import SafecompControllerRunner


if __name__ == "__main__":
    BUILD_PATH = Path("./build").absolute()
    RUNS_PATH = Path("./runs")

    if RUNS_PATH.exists():
        shutil.rmtree(RUNS_PATH)
    if not RUNS_PATH.exists():
        RUNS_PATH.mkdir(parents=True, exist_ok=True)

    t = TemporalLogicConfiguration("zadeh", quantitative=True)

    w = SafetyWorldConfiguration()
    w.wp_start.duration = 30.0
    w.wp_bench.duration = 2.0
    w.wp_wait.duration = 4.0
    w.wp_cell.duration = 8.0
    w.wp_exit.duration = 16.0

    c = DigitalTwinConfiguration(w, SafetyBuildConfiguration(BUILD_PATH), t)
    s = SafecompControllerRunner(RUNS_PATH, c)
    s.run()
    print(s.path)

    w.wp_start.duration = random.random() * 5.0

    c = DigitalTwinConfiguration(w, SafetyBuildConfiguration(BUILD_PATH), t)
    s = SafecompControllerRunner(RUNS_PATH, c)
    s.run()
    print(s.path)
