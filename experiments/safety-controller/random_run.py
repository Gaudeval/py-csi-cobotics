from pathlib import Path
from drs import drs
from tqdm import trange

from wrapper.configuration import SafetyWorldConfiguration, SafetyRunnerConfiguration
from wrapper.runner import SafetyBuildRunner

# https://pypi.org/project/drs/

if __name__ == "__main__":
    BUILD_PATH = Path("./build").absolute()
    RUNS_COUNT = 10

    for _ in trange(RUNS_COUNT):
        s = drs(5, 30.0)

        w = SafetyWorldConfiguration()
        w.wp_start.duration = s[0]
        w.wp_bench.duration = s[1]
        w.wp_wait.duration = s[2]
        w.wp_cell.duration = s[3]
        w.wp_exit.duration = s[4]

        c = SafetyRunnerConfiguration(w, BUILD_PATH)

        r = SafetyBuildRunner("./runs", c)

        r.run()
