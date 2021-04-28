"""Reprocess the output of runs in a given repository to generate new traces and reports."""
import json
import tqdm

from csi.experiment import Repository, Experiment, Run
from csi.monitor import Monitor
from csi.safety import SafetyCondition

from wrapper.utils import as_working_directory
from wrapper.runner import SafetyDigitalTwinRunner


if __name__ == "__main__":
    t: Repository = Repository("./runs")
    e: Experiment
    r: Run
    completed_runs = list(t.completed_runs)
    for e, r in tqdm.tqdm(completed_runs):
        assert isinstance(e, SafetyDigitalTwinRunner)
        print(r.work_path)
        with as_working_directory(r.work_path):
            trace, predicates = e.process_output()

            report = {}
            safety_condition: SafetyCondition
            for safety_condition in predicates:
                i = Monitor(frozenset()).evaluate(
                    trace,
                    safety_condition.condition,
                    dt=0.01,
                    quantitative=e.configuration.ltl.quantitative,
                    logic=e.configuration.ltl.logic,
                )
                print(f"\t{safety_condition.uid}:{i}")
                report[safety_condition.uid] = i
            with open("./hazard-report.json", "w") as json_report:
                json.dump(report, json_report, indent=4)
