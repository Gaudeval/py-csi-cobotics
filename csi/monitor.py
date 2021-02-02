from __future__ import annotations

import attr
import funcy
import lenses
from traces import TimeSeries
from typing import (
    Any,
    Callable,
    List,
    Mapping,
    Optional,
    Tuple,
    Iterable,
    Set,
    FrozenSet,
    Dict,
    MutableMapping,
)

from csi.safety import Atom, Node


PathType = Tuple[str]


@attr.s(
    auto_attribs=True,
    repr=True,
    slots=True,
    eq=True,
    order=True,
    hash=True,
)
class Context:
    path: PathType = attr.ib(tuple())

    def __set_name__(self, owner, name):
        self.name = name

    def __get__(self, instance, owner):
        return self.__build(getattr(instance, "path", tuple()) + (self.name,))

    @classmethod
    def __build(cls, path):
        return cls(path)


@attr.s(
    auto_attribs=True,
    repr=True,
    slots=True,
    eq=True,
    order=True,
    hash=True,
)
class Alias:
    condition: Node

    def __get__(self, instance, owner):
        path = getattr(instance, "path", tuple())
        atoms = set(lenses.bind(self.condition.walk()).Each().Instance(Atom).collect())
        v = {a.id: Atom(path + a.id) for a in atoms if isinstance(a.id, tuple)}
        return self.condition[v]


class Term:
    def __set_name__(self, owner, name):
        self._name = name

    def __get__(self, instance, owner):
        return Atom(getattr(instance, "path", tuple()) + (self._name,))


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
    """Group of conditions to verify """

    conditions: FrozenSet[Node] = attr.ib(frozenset())

    def __iadd__(self, other: Node) -> Monitor:
        return Monitor(self.conditions | {other})

    def __ior__(self, other: Monitor) -> Monitor:
        return self | other

    def __or__(self, other: Monitor) -> Monitor:
        return Monitor(self.conditions | other.conditions)

    def atoms(self, condition=None) -> Set[Atom]:
        reference = self.conditions if condition is None else {condition}
        return {a for c in reference for a in c.walk() if isinstance(a, Atom)}

    def evaluate(
        self,
        trace: Trace,
        condition: Optional[Node] = None,
        *,
        dt=1.0,
        time: Any = False
    ) -> Mapping[Node, Optional[bool]]:
        evaluated_conditions: Iterable[Node] = (
            self.conditions if condition is None else {condition}
        )

        results: MutableMapping[Node, Optional[bool]] = dict()
        for phi in evaluated_conditions:
            signals = trace.project(self.atoms(phi))
            if all(a.id in signals for a in self.atoms(phi)):
                r = phi(signals, dt=dt, time=time)
                if time is None:
                    r = funcy.walk_values(lambda v: v > 0, r)
                else:
                    r = r > 0
                results[phi] = r
            else:
                results[phi] = None
        return results if condition is None else funcy.first(results.values())


class Trace:
    values: Dict[PathType, TimeSeries]

    def __init__(self):
        self.values = {}

    def atoms(self) -> Set[Atom]:
        return {Atom(k) for k in self.values.keys()}

    def project(self, atoms: Iterable[Atom]) -> Mapping[str, List[(int, Any)]]:
        results = {}
        for a in set(atoms) & self.atoms():
            results[a.id] = []
            for (t, v) in self.values[a.id].items():
                if isinstance(v, bool):
                    results[a.id].append((t, 1 if v else -1))
                else:
                    results[a.id].append((t, v))
        return results

    @staticmethod
    def _merge_values(values: List[Optional[TimeSeries]]):
        return funcy.last(i for i in values if i is not None)

    def update(self, other: Trace) -> Trace:
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
        if isinstance(element, Mapping):
            element = [element]
        for e in element:
            t = timestamp(e)
            if t is None:
                continue
            for path, value in self._extract_atom_values(e):
                self.values[path][t] = value

    def __setitem__(self, key: Atom, value: Tuple[int, Any]):
        t, v = value
        if key.id not in self.values:
            self.values[key.id] = TimeSeries()
        self.values[key.id][t] = v
