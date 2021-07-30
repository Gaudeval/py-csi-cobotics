import collections
import json
import pickle
import random
from pathlib import Path

from csi.coverage import EventCombinationsRegistry
from csi.experiment import Repository, Run
from csi.twin.configuration import DigitalTwinConfiguration, TemporalLogicConfiguration
from scenarios.tcx.safety.hazards import hazards
from scenarios.tcx.safety.ucas import unsafe_control_actions
from wrapper.configuration import SafetyWorldConfiguration, SafetyBuildConfiguration
from wrapper.runner import SafecompControllerRunner
from wrapper.utils import as_working_directory
from wrapper.fitness import RunnerFitnessWrapper


if __name__ == "__main__":
    BUILD_PATH = Path("./build").absolute()
    RUNS_PATH = Path("./runs")

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

    else:
        x: Repository = Repository("runs")
        r: Run
        for e, r in x.runs:
            e: SafecompControllerRunner
            with as_working_directory(r.work_path):
                # Reprocess output
                t, c = e.process_output()
                e.produce_safety_report(t, c, quiet=True)
                # Display encountered safety conditions
                sc = list(hazards) + list(unsafe_control_actions)
                with Path("hazard-report.json").open() as json_report:
                    report = json.load(json_report)
                    for uid, occurs in report.items():
                        if occurs:
                            c = next(i for i in sc if i.uid == uid)
                            print(c.uid, c.description)
                # Compute coverage
                with e.event_combinations_output.open("rb") as combinations_file:
                    g: EventCombinationsRegistry = pickle.load(combinations_file)
                    # print(f"Coverage: {g.covered}/{g.total} ({g.coverage})")
                    pass

            # Compute experiment score
            s = RunnerFitnessWrapper(logic="zadeh").score_experiment(e)
            print(s)

        SafecompControllerRunner.merge_coverage(x)
