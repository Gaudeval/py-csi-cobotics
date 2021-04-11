from pathlib import Path

from wrapper.configuration import SafetyWorldConfiguration, SafetyRunnerConfiguration
from wrapper.runner import SafetyBuildRunner


if __name__ == "__main__":
    BUILD_PATH = Path("./build").absolute()

    w = SafetyWorldConfiguration()
    w.wp_start.duration = 0.0
    w.wp_bench.duration = 2.0
    w.wp_wait.duration = 4.0
    w.wp_cell.duration = 8.0
    w.wp_exit.duration = 16.0

    c = SafetyRunnerConfiguration(w, BUILD_PATH)

    r = SafetyBuildRunner("./runs", c)

    r.run()
