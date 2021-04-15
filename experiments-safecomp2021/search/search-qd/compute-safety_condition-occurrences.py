import json
from collections import defaultdict
from tqdm import tqdm

from csi.experiment import Repository, RunStatus
from csi.monitor import Monitor
from scenarios.tcx import unsafe_control_actions, hazards, TcxDigitalTwinRunner
from scenarios.tcx.monitor import P


def compute_occurrence_profile():
    H = set(h.uid for h in hazards)
    U = set(u.uid for u in unsafe_control_actions)
    sc_occurrences = defaultdict(set)
    for runs in tqdm(
        [
            "../search-ran/runs",
            "./backup-5-crisp/runs",
            "./backup-4-stop in cell/runs",
            "./backup-3-no stop in cell/runs",
            "../search-ga/backup-1-minimise/runs",
            "../search-ga/backup-2-maximise/runs",
        ],
        desc="Runs",
    ):
        repository = Repository(runs)
        for experiment in tqdm(repository.experiments, desc="Experiment"):
            for run in experiment.runs:
                if run.status == RunStatus.COMPLETE:
                    k = [False, False]
                    with (run.work_path / "hazard-report.json").open() as json_report:
                        report = json.load(json_report)
                        for uid, occurs in report.items():
                            if occurs is None:
                                continue
                            # FIXME
                            if uid == "UCA9-T-1":
                                continue
                            # if uid not in ["3", "UCA9-P-2"]:
                            #    continue
                            occurs = min(1, max(0, float(occurs)))
                            if occurs >= 1:
                                if uid in H:
                                    k[0] = True
                                if uid in U:
                                    k[1] = True
                    sc_occurrences[tuple(k)].add(run)
                    break
    return sc_occurrences


def check_run(run):
    run_db = run.work_path / "output.sqlite"
    run_trace, _ = TcxDigitalTwinRunner.process_output(run_db, [])
    # Compute predicate values at each point in time
    monitor = Monitor()
    # 3
    v = monitor.evaluate(run_trace, P.assembly.is_damaged.eventually())
    print("[3] Assembly damaged", v)
    v = monitor.evaluate(run_trace, P.operator.is_damaged.eventually())
    print("[3] Operator damaged", v)
    # 1.3
    v = monitor.evaluate(run_trace, P.operator.position.in_workspace.eventually())
    print("[1.3] Operator in cell", v)
    v = monitor.evaluate(run_trace, P.operator.position.in_bench.eventually())
    print("[1.3] Operator in bench", v)
    v = monitor.evaluate(run_trace, P.operator.position.in_tool.eventually())
    print("[1.3] Operator in tool", v)
    # 1.2
    for i in ["in_bench", "in_workspace", "in_tool"]:
        x = (
            P.cobot.velocity.gt(getattr(P.constraints.cobot.velocity, i))
            & getattr(P.cobot.position, i)
        ).eventually()
        v = monitor.evaluate(run_trace, x)
        print("[1.2] Cobot at {}".format(i), v)


def extract_occurring_sc(run):
    with (run.work_path / "hazard-report.json").open() as json_report:
        report = json.load(json_report)
        s = {}
        for uid, occurs in report.items():
            if occurs is None:
                continue
            if uid not in ["3", "UCA9-P-2"]:
                continue
            occurs = min(1, max(0, float(occurs)))
            if occurs >= 1:
                s[uid] = occurs
    return s


if __name__ == "__main__":
    sc_occurrences = compute_occurrence_profile()
    for k, runs in sc_occurrences.items():
        print(k, len(runs))

    # exit(0)
    print("======")
    for r in sc_occurrences[(True, False)]:
        print(r.work_path, extract_occurring_sc(r))
    #        check_run(r)
