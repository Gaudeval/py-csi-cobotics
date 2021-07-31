import dataset
import pickle
import timeit

import mtl.connective
import tqdm

from pathlib import Path

from mtl import BOT
from traces import TimeSeries
from typing import Any, Iterator

from csi.coverage import Domain
from csi.experiment import Repository, Run
from csi.monitor import Trace, Monitor
from csi.safety import Atom, Node, SafetyCondition

from wrapper.runner import SafecompControllerRunner
from wrapper.utils import as_working_directory

default_runner = SafecompControllerRunner(".", None)

domain: dict[Atom, Domain] = default_runner.initialise_registry().domain
conditions: list[SafetyCondition] = default_runner.safety_conditions
# FIXME Boolean predicates for le/ge operators are split in two, lt and eq. Covering eq is highly unlikely
predicates: set[Node] = default_runner.extract_boolean_predicates(conditions)


def sanitise_name(condition: SafetyCondition):
    return condition.uid.replace("-", "_").replace(".", " ")


def collect_states(trace: Trace) -> Iterator[tuple[float, set[tuple[str, Any]]]]:
    event_keys: list[Atom] = sorted(domain, key=lambda d: d.id)
    events: TimeSeries = TimeSeries.merge([trace.values[e.id] for e in event_keys])
    events.compact()
    t: float
    # TODO Filter values used in monitor, e.g. ignore unused atoms in any safety condition
    for t, v in events.items():
        s = set()
        for (e, d), i in zip(sorted(domain.items(), key=lambda d: d[0].id), v):
            s.add(("_".join(e.id), d.value(i)))
        yield t, s


def collect_predicates(trace: Trace):
    # -> Iterator[tuple[float, set[tuple[str, bool]]]]:
    predicate_keys = sorted(predicates, key=lambda d: str(d))
    predicate_values = list()
    for predicate in predicate_keys:
        v = Monitor().evaluate(
            trace,
            predicate,
            dt=0.01,
            quantitative=True,
            logic=mtl.connective.zadeh,
            time=None,
        )
        v = [(t, c >= mtl.connective.zadeh.const_true) for t, c in v]
        ts: TimeSeries = TimeSeries(v)
        ts.compact()
        predicate_values.append(ts)
    #
    events: TimeSeries = TimeSeries.merge(predicate_values)
    for t, v in events.items():
        s = set()
        for e, i in zip(predicate_keys, v):
            s.add((e, i))
        yield t, s


def collect_conditions(run: Run, trace: Trace):
    for condition in conditions:
        if condition.condition == BOT:
            continue
        i = Monitor().evaluate(
            trace,
            condition.condition,
            dt=0.01,
            quantitative=run.experiment.configuration.ltl.quantitative,
            logic=run.experiment.configuration.ltl.logic,
        )
        yield condition, i >= run.experiment.configuration.ltl.logic.const_true


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
    test_insert: bool = True
    test_coverage: bool = True
    repository = Path(
        "C:\\Users\\Benjamin\\Data\\repositories\\safecomp-revised\\runs.ran"
    )
    # repository = Path("runs")
    #
    db: dataset.Database
    states_table: dataset.Table
    predicates_table: dataset.Table
    conditions_table: dataset.Table
    #
    db = dataset.connect("sqlite:///test.db")
    states_table = db["states"]
    predicates_table = db["predicates"]
    pred_value_table = db["predicates_values"]
    conditions_table = db["conditions"]
    #
    if test_insert:
        timer_start = timeit.default_timer()
        # Assign unique id to predicates
        predicate_ids: dict[Node, int] = dict()
        for predicate in predicates:
            row = predicates_table.find_one(predicate=str(predicate))
            if row is not None:
                predicate_ids[predicate] = row["id"]
            else:
                i = predicates_table.insert_ignore(
                    {"predicate": str(predicate)},
                    ["predicate"],
                    ensure=True,
                )
                predicate_ids[predicate] = i
        db.commit()
        #
        for run, trace in tqdm.tqdm(collect_traces(repository)):
            for timestamp, state in collect_states(trace):
                meta = {"run": str(run.uuid), "timestamp": timestamp}
                states_table.insert(dict(state) | meta, ensure=True)
            db.commit()
            #
            for timestamp, state in collect_predicates(trace):
                meta = {"run": str(run.uuid), "timestamp": timestamp}
                pred_value_table.insert(
                    {str(predicate_ids[p]): v for p, v in state} | meta, ensure=True
                )
            db.commit()
            #
            meta = {"run": str(run.uuid)}
            conditions_table.insert(
                {sanitise_name(c): v for c, v in collect_conditions(run, trace)},
                ensure=True,
            )
        timer_end = timeit.default_timer()
        print(f"Insertion duration: {timer_end - timer_start}")
    if test_coverage:
        timer_start = timeit.default_timer()
        # Atom coverage
        domain_columns = {"_".join(a.id): d for a, d in domain.items()}
        atoms_covered = 0
        atoms_count = sum(len(d) for d in domain_columns.values())
        for atom_column in sorted(domain_columns):
            atom_covered = sum(1 for _ in states_table.distinct(atom_column))
            print(
                f"Atom '{atom_column}': {atom_covered} / {len(domain_columns[atom_column])}"
            )
            atoms_covered += atom_covered
        # Predicate coverage
        predicate_columns = {str(i + 1) for i in range(len(predicates))}
        predicates_covered = 0
        predicates_count = 2 * len(predicates)
        for predicate_column in sorted(predicate_columns):
            predicate_covered = sum(
                1 for _ in pred_value_table.distinct(predicate_column)
            )
            predicate = predicates_table.find_one(id=int(predicate_column))["predicate"]
            print(f"Predicate '{predicate}': {predicate_covered} / 2")
            predicates_covered += predicate_covered
        # Condition/Safety coverage
        condition_columns = {sanitise_name(c) for c in conditions}
        condition_columns = condition_columns & set(conditions_table.columns)
        conditions_covered = 0
        conditions_count = 2 * len(condition_columns)
        for condition_column in sorted(condition_columns):
            condition_covered = sum(
                1 for _ in conditions_table.distinct(condition_column)
            )
            print(f"Condition '{condition_column}': {condition_covered} / 2")
            conditions_covered += condition_covered
        timer_end = timeit.default_timer()
        print(f"Atom coverage: {atoms_covered / atoms_count}")
        print(f"               {atoms_covered} / {atoms_count}")
        print(f"Pred coverage: {predicates_covered / predicates_count}")
        print(f"               {predicates_covered} / {predicates_count}")
        print(f"Cond coverage: {conditions_covered / conditions_count}")
        print(f"               {conditions_covered} / {conditions_count}")
        print(f"     duration: {timer_end - timer_start}")
    db.close()
