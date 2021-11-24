"""
Collection of events occurring in the system and monitoring of situation occurrences.

"""
from __future__ import annotations
import itertools
from typing import (
    FrozenSet,
    Set,
    Optional,
    Any,
    Mapping,
    Iterable,
    MutableMapping,
    Dict,
    List,
    Tuple,
    Callable,
)

import attr
import funcy
from mtfl import AtomicPred
from mtfl.ast import BinaryOpMTL
from mtfl.connective import _ConnectivesDef, default
from traces import TimeSeries

from csi.situation.components import Node, _Atom, PathType


@attr.s(
    frozen=True,
    auto_attribs=True,
    repr=True,
    slots=True,
    eq=True,
    order=False,
    hash=True,
)
class Monitor:
    """Ensemble of temporal logic conditions"""

    conditions: FrozenSet[Node] = attr.ib(factory=frozenset)

    def __iadd__(self, other: Node) -> Monitor:
        return Monitor(self.conditions | {other})

    def __ior__(self, other: Monitor) -> Monitor:
        return self | other

    def __or__(self, other: Monitor) -> Monitor:
        return Monitor(self.conditions | other.conditions)

    def atoms(self, condition=None) -> Set[_Atom]:
        """Extract the atoms used in the monitor or the specified condition"""
        reference = self.conditions if condition is None else {condition}
        return {a for c in reference for a in c.walk() if isinstance(a, _Atom)}

    def extract_boolean_predicates(self, conditions=None) -> Set[Node]:
        """Extract the boolean predicates used in the monitor or the specified conditions."""
        terms: Set[AtomicPred] = set()
        comparisons: Set[BinaryOpMTL] = set()
        conditions = self.conditions if conditions is None else conditions
        # Extract all candidates
        for s in conditions:
            local_comparisons = set()
            for p in s.condition.walk():
                if isinstance(p, AtomicPred):
                    terms.add(p)
                if isinstance(p, BinaryOpMTL):
                    local_comparisons.add(p)
            # Remove a = b cases resulting from a <= b in condition s
            for p in list(local_comparisons):
                if any(
                    c.children == p.children and p.OP == "=" and c.OP == "<"
                    for c in local_comparisons
                ):
                    local_comparisons.remove(p)
            comparisons.update(local_comparisons)
        # Remove values used in comparisons
        for p in comparisons:
            terms = terms.difference(p.children)
        return set(itertools.chain(terms, comparisons))

    def evaluate(
        self,
        trace: Trace,
        condition: Optional[Node] = None,
        *,
        dt=1.0,
        time: Any = False,
        quantitative=False,
        logic: _ConnectivesDef = default
    ) -> Mapping[Node, Optional[bool]]:
        """Evaluate the truth values of the monitor conditions on the specified trace."""
        evaluated_conditions: Iterable[Node] = (
            self.conditions if condition is None else {condition}
        )

        results: MutableMapping[Node, Optional[bool]] = dict()
        for phi in evaluated_conditions:
            signals = {
                k.id: v for k, v in trace.project(self.atoms(phi), logic).items()
            }
            # FIXME A default value is required by mtl even if no atoms required (TOP/BOT)
            signals[None] = [(0, logic.const_false)]
            if all(a.id in signals for a in self.atoms(phi)):
                r = phi(signals, dt=dt, time=time, logic=logic)
                if not quantitative:
                    if time is None:
                        r = funcy.walk_values(lambda v: v >= logic.const_true, r)
                    else:
                        r = r >= logic.const_true
                results[phi] = r
            else:
                results[phi] = None
        return results if condition is None else funcy.first(results.values())


class Trace:
    """Trace of situation components' value over time"""

    values: Dict[_Atom, TimeSeries]

    def __init__(self):
        self.values = {}

    def atoms(self) -> Set[_Atom]:
        """Extract the atoms which values has been defined in the trace"""
        return set(self.values.keys())

    def project(
        self, atoms: Iterable[_Atom], logic=default
    ) -> Mapping[_Atom, List[(int, Any)]]:
        """Reduce the trace to the specified atoms"""
        results = {}
        for a in set(atoms) & self.atoms():
            results[a] = []
            for (t, v) in self.values[a].items():
                if isinstance(v, bool):
                    results[a].append((t, logic.const_true if v else logic.const_false))
                else:
                    results[a].append((t, v))
        return results

    @staticmethod
    def _merge_values(values: List[Optional[TimeSeries]]):
        return funcy.last(i for i in values if i is not None)

    def update(self, other: Trace) -> Trace:
        """Update the values of the current trace with the other"""
        for t, s in other.values.items():
            c = self.values.get(t, TimeSeries())
            self.values[t] = TimeSeries.merge([c, s], operation=self._merge_values)
        return self

    def __ior__(self, other: Trace) -> Trace:
        return self | other

    def __or__(self, other: Trace) -> Trace:
        return Trace().update(self).update(other)

    @classmethod
    def _extract_atom_values(
        cls, element: Any, prefix: PathType = ()
    ) -> Iterable[Tuple[PathType, Any]]:
        """Convert nested structure into flat list with tuple capturing nested paths."""
        if isinstance(element, Mapping):
            return funcy.cat(
                cls._extract_atom_values(v, prefix + (k,)) for k, v in element.items()
            )
        if isinstance(element, list):
            return funcy.cat(
                cls._extract_atom_values(v, prefix + (str(i),))
                for i, v in enumerate(element)
            )
        return [(prefix, element)]

    def record(self, element: Any, *, timestamp: Callable[[Mapping], int]) -> None:
        """Record the values encoded in the element at the specified time"""
        # TODO Assess if the record method still behaves as expected following the atom refactoring
        if isinstance(element, Mapping):
            element = [element]
        for e in element:
            t = timestamp(e)
            if t is None:
                continue
            for path, value in self._extract_atom_values(e):
                if path not in self.values:
                    self.values[path] = TimeSeries()
                self.values[path][t] = value

    def __setitem__(self, key: _Atom, value: Tuple[float, Any]):
        t, v = value
        k = key
        if k not in self.values:
            self.values[k] = TimeSeries()
        # FIXME Events occuring at the same time
        #        e = self.values[k]
        #        while t in e._d:
        #            t += 0.0001
        self.values[k][t] = v
