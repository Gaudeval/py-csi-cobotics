"""Export the traces of traversed runs into readable json format"""
import collections
import json
import pickle
from pathlib import Path

from csi.experiment import Repository, Run
from wrapper.runner import SafetyDigitalTwinRunner

if __name__ == "__main__":
    RUNS_PATH = Path("./runs-replays")
    t: Repository = Repository(RUNS_PATH)
    e: SafetyDigitalTwinRunner
    r: Run
    for e, r in t.completed_runs:
        print(e.uuid)
        with (r.work_path / e.trace_output).open("rb") as trace_file:
            trace = pickle.load(trace_file)
        with (r.work_path / "hazard-report.json").open("r") as hazard_file:
            hazards = json.load(hazard_file)
        json_trace = []
        json_ts = collections.defaultdict(list)
        for name, ts in sorted(trace.values.items()):
            json_values = []
            ts.compact()
            for t, v in ts.items():
                json_ts[t].append((name[0], str(v)))
                json_values.append((t, str(v)))
            json_trace.append((name, json_values))
        with (RUNS_PATH / "{}.json".format(e.uuid)).open("w") as json_file:
            json.dump(
                (
                    hazards,
                    json_trace,
                    list(
                        map(
                            str,
                            sorted(
                                (
                                    t,
                                    " ".join(
                                        list(
                                            "({0},{1})".format(i, j)
                                            for i, j in sorted(v)
                                        )
                                    ),
                                )
                                for t, v in json_ts.items()
                            ),
                        )
                    ),
                ),
                json_file,
                indent=4,
            )
