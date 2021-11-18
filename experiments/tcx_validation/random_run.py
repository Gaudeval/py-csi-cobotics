from pathlib import Path
from drs import drs
from tqdm import trange

from wrapper.configuration import SceneConfiguration, BuildConfiguration, RunnerConfiguration
from wrapper.runner import SafetyDigitalTwinRunner

if __name__ == "__main__":
    BUILD_PATH = Path("./build-server").absolute()
    RUNS_PATH = Path("./runs")
    RUNS_COUNT = 100

    for _ in trange(RUNS_COUNT):
        s = drs(5, 20.0)

        w = SceneConfiguration()
        w.wp_start.duration = s[0]
        w.wp_bench.duration = s[1]
        w.wp_wait.duration = s[2]
        w.wp_cell.duration = s[3]
        w.wp_exit.duration = 60.0  # s[4]

        c = RunnerConfiguration(w, BuildConfiguration(BUILD_PATH))

        r = SafetyDigitalTwinRunner(RUNS_PATH, c)

        r.run()
