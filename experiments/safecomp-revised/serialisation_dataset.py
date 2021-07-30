import dataset
import pickle
import timeit
import tqdm

from pathlib import Path
from traces import TimeSeries
from typing import Any, Iterator

from csi.coverage import Domain
from csi.experiment import Repository, Run
from csi.monitor import Trace
from csi.safety import Atom

from wrapper.runner import SafecompControllerRunner
from wrapper.utils import as_working_directory


domain: dict[Atom, Domain] = SafecompControllerRunner.initialise_registry(None).domain


def collect_states(trace: Trace) -> Iterator[tuple[float, set[tuple[str, Any]]]]:
    event_keys: list[Atom] = sorted(domain, key=lambda d: d.id)
    events: TimeSeries = TimeSeries.merge([trace.values[e.id] for e in event_keys])
    events.compact()
    t: float
    for t, v in events.items():
        s = set()
        for (e, d), i in zip(sorted(domain.items(), key=lambda d: d[0].id), v):
            s.add(("_".join(e.id), d.value(i)))
        yield t, s


def collect_traces(repository_path: Path) -> Iterator[tuple[Run, Trace]]:
    x: Repository = Repository(repository_path)
    r: Run
    e: SafecompControllerRunner
    for e, r in x.runs:
        with as_working_directory(r.work_path):
            # Load run event trace
            with e.trace_output.open("rb") as trace_file:
                t: Trace = pickle.load(trace_file)
                yield r, t


if __name__ == "__main__":
    #
    test_insert: bool = False
    test_coverage: bool = True
    repository = Path(
        "C:\\Users\\Benjamin\\Data\\repositories\\safecomp-revised\\runs.ran"
    )
    #
    db: dataset.Database
    states: dataset.Table
    #
    db = dataset.connect("sqlite:///dataset.test.db")
    states = db["states"]
    #
    if test_insert:
        timer_start = timeit.default_timer()
        for run, trace in tqdm.tqdm(collect_traces(repository)):
            for timestamp, state in collect_states(trace):
                meta = {"run": str(run.uuid), "timestamp": timestamp}
                states.insert(dict(state) | meta, ensure=True)
            db.commit()
        timer_end = timeit.default_timer()
        print(f"Insertion duration: {timer_end - timer_start}")
    if test_coverage:
        domain_columns = {"_".join(a.id): d for a, d in domain.items()}
        # Atom coverage
        timer_start = timeit.default_timer()
        atoms_covered = 0
        atoms_count = sum(len(d) for d in domain_columns.values())
        for atom_column in sorted(domain_columns):
            atom_covered = sum(1 for _ in states.distinct(atom_column))
            print(
                f"Atom '{atom_column}': {atom_covered} / {len(domain_columns[atom_column])}"
            )
            atoms_covered += atom_covered
        timer_end = timeit.default_timer()
        print(f"Atom coverage: {atoms_covered / atoms_count}")
        print(f"               {atoms_covered} / {atoms_count}")
        print(f"     duration: {timer_end - timer_start}")
    db.close()
