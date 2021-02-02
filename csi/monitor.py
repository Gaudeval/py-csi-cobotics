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
            atoms = trace.project(self.atoms(phi))
            if all(a.id in atoms for a in Monitor().atoms(phi)):
                r = phi(atoms, dt=dt, time=time)
                if time is None:
                    r = [(t, v > 0) for t, v in r]
                else:
                    r = r > 0
                results[phi] = r
            else:
                results[phi] = None
        if condition is not None:
            return next(iter(results.values()))
        return results


class Trace:
    values: Dict[PathType, TimeSeries]

    def __init__(self):
        self.values = {}

    def atoms(self) -> Set[Atom]:
        return {Atom(k) for k in self.values.keys()}

    def project(self, atoms: Iterable[Atom]) -> Mapping[str : List[(int, Any)]]:
        return {
            a.id: [(t, v) for t, v in self.values[a.id]]
            for a in atoms
            if a.id in self.values
        }

    @staticmethod
    def _merge_values(values: List[Optional[TimeSeries]]):
        n = [i for i in values if i is not None]
        return n[-1] if n else None

    def update(self, other: Trace) -> None:
        for t, s in other.values.items():
            if t in self.values:
                self.values[t] = TimeSeries.merge(
                    [self.values[t], s], operation=self._merge_values
                )
            else:
                self.values[t] = TimeSeries(s)

    def __ior__(self, other: Trace) -> Trace:
        return self | other

    def __or__(self, other: Trace) -> Trace:
        result = Trace()
        result.update(self)
        result.update(other)
        return result

    @classmethod
    def _extract_atom_values(
        cls, element: Any, prefix: PathType = ()
    ) -> Iterable[Tuple[PathType, Any]]:
        """Convert nested structure into flat list with tuple capturing nested paths."""
        if isinstance(element, dict):
            return funcy.cat(
                cls._extract_atom_values(v, prefix + (k,)) for k, v in element.items()
            )
        if isinstance(element, list):
            return funcy.cat(
                cls._extract_atom_values(v, prefix + (str(i),))
                for i, v in enumerate(element)
            )
        return [(prefix, element)]

    def _record(self, element: Any, timestamp: Callable[[Any], int]) -> None:
        time = timestamp(element)
        if time is None:
            return
        for path, value in self._extract_atom_values(element):
            path @= (time, value)

    def record(self, element: Any, *, timestamp: Callable[[Mapping], int]) -> None:
        if isinstance(element, dict):
            self._record(element, timestamp)
        else:
            for e in element:
                self.record(e, timestamp=timestamp)

    def __setitem__(self, key: Atom, value: Tuple[int, Any]):
        t, v = value
        if key.id not in self.values:
            self.values[key.id] = TimeSeries()
        self.values[key.id][t] = v
