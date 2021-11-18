from pathlib import Path

from wrapper.configuration import RunnerConfiguration, SceneConfiguration, BuildConfiguration
from wrapper.runner import SafetyDigitalTwinRunner


if __name__ == "__main__":
    BUILD_PATH = Path("./build").absolute()

    w = SceneConfiguration()
    w.wp_start.duration = 0.0
    w.wp_bench.duration = 2.0
    w.wp_wait.duration = 4.0
    w.wp_cell.duration = 8.0
    w.wp_exit.duration = 16.0

    c = RunnerConfiguration(w, BuildConfiguration(BUILD_PATH))

    r = SafetyDigitalTwinRunner("./runs", c)

    r.run()
    print(r.path)
