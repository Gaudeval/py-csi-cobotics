"""
Compute observed states and coverage metrics for an experiment repository.

This script builds a set of system states observed across experiments. States
are defined based on the domain defined for the use-case, that is the set of
atoms and their domain values. The occurrence of safety conditions and their
components are also tracked.

All sampled information can be stored in a report database. A coverage report
is produced as part of the script.
"""
import dataset
import pickle
import timeit

import mtfl.connective
import tqdm

from pathlib import Path

from mtfl import BOT
from traces import TimeSeries
from typing import Any, Iterator, Iterable, Dict

from csi import Repository, Run, SafetyCondition
from csi.situation import Domain, Monitor, Trace
from csi.situation.components import _Atom, Node

from wrapper.fitness import RunnerFitnessWrapper
from wrapper.runner import SafecompControllerRunner
from wrapper.utils import as_working_directory

default_runner = SafecompControllerRunner(".", None)
conditions: list[SafetyCondition] = default_runner.safety_conditions
predicates: set[Node] = Monitor().extract_boolean_predicates(conditions)


def compute_domain():
    e: Dict[_Atom, Domain] = {}
    for atom in Monitor(frozenset(c.condition for c in conditions)).atoms():
        if atom.domain is not None:
            e[atom] = atom.domain
    return e


# FIXME domain is empty, fix computation
domain: Dict[_Atom, Domain] = compute_domain()


def sanitise_name(condition: SafetyCondition):
    return condition.uid.replace("-", "_").replace(".", " ")


def collect_states(
    trace: Trace, conditions: Iterable[SafetyCondition]
) -> Iterator[tuple[float, set[tuple[str, Any]]]]:
    atoms = set(domain.keys()) | set(
        Monitor(frozenset(c.condition for c in conditions)).atoms()
    )
    event_keys: list[_Atom] = sorted(atoms, key=lambda d: d.id)
    events: TimeSeries = TimeSeries.merge([trace.values[e] for e in event_keys])
    events.compact()
    t: float
    for t, v in events.items():
        s = set()
        for e, i in zip(event_keys, v):
            if e in domain:
                d = domain[e]
                s.add((e.id, d.value(i)))
            else:
                s.add((e.id, i))
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
            logic=mtfl.connective.zadeh,
            time=None,
        )
        v = [(t, c >= mtfl.connective.zadeh.const_true) for t, c in v]
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
        yield condition, i >= run.experiment.configuration.ltl.logic.const_true, i


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
    test_db: bool = True
    repository = Path("runs")
    #
    db: dataset.Database
    states_table: dataset.Table
    predicates_table: dataset.Table
    conditions_table: dataset.Table
    #
    if test_db:
        if test_insert:
            Path("test.db").unlink(missing_ok=True)
        db = dataset.connect("sqlite:///test.db")
    else:
        db = dataset.connect(
            "sqlite:///;Synchronous=NORMAL;Journal Mode=WAL;Temp Store=MEMORY;"
        )
    states_table = db["states"]
    predicates_table = db["predicates"]
    pred_value_table = db["predicates_values"]
    conditions_table = db["conditions"]
    fuzzy_conditions_table = db["conditions_fuzzy"]
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
            fitness = -RunnerFitnessWrapper(with_features=False).score_report(
                "hazard-report.json"
            )
            #
            for timestamp, state in collect_states(trace, conditions):
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
            meta = {"run": str(run.uuid), "fitness": fitness}
            condition_values = {
                sanitise_name(c): (v, i) for c, v, i in collect_conditions(run, trace)
            }
            conditions_table.insert(
                {k: v for k, (v, _) in condition_values.items()} | meta,
                ensure=True,
            )
            fuzzy_conditions_table.insert(
                {k: v for k, (_, v) in condition_values.items()} | meta,
                ensure=True,
            )
        timer_end = timeit.default_timer()
        print(f"Insertion duration: {timer_end - timer_start}")
    if test_coverage:
        timer_start = timeit.default_timer()
        # Atom coverage
        condition_atoms = set(
            Monitor(frozenset(c.condition for c in conditions)).atoms()
        )
        domain_columns = {a.id: d for a, d in domain.items() if a in condition_atoms}
        domain_columns = {
            a: d for a, d in domain_columns.items() if a in states_table.columns
        }
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
            v = list(conditions_table.distinct(condition_column))
            condition_covered = sum(1 for _ in v)
            observed = any(c[condition_column] for c in v)
            print(
                f"Condition '{condition_column}': {condition_covered} / 2 (Seen: {observed})"
            )
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
