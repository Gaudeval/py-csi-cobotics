from __future__ import annotations

import attr
import funcy
from lenses import bind
from traces import TimeSeries
from typing import Any, Callable, List, Mapping, Optional, Tuple, Union, Iterable, Set, TypeVar, FrozenSet

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
    path: PathType

    def __set_name__(self, owner, name):
        self.name = name

    def __get__(self, instance, owner):
        return self.__build(getattr(instance, "path", tuple()) + (self.name,))

    @classmethod
    def __build(cls, path):
        return cls(path)


class Term:
    def __set_name__(self, owner, name):
        self._name = name

    def __get__(self, instance, owner):
        return getattr(instance, "path", tuple()) + (self._name,)


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

    conditions: FrozenSet[Node]

    def __iadd__(self, other: Node) -> Monitor:
        return Monitor(self.conditions | {other})

    def __ior__(self, other: Monitor) -> Monitor:
        return self | other

    def __or__(self, other: Monitor) -> Monitor:
        return Monitor(self.conditions | other.conditions)

    def atoms(self) -> Iterable[Atom]:
        return bind(self.conditions).F(lambda c: c.walk()).Instance(Atom).collect()

    def evaluate(self, trace: Trace, condition: Optional[Node]) -> Mapping[Node, Optional[bool]]:
        pass


class Trace:
    values: Mapping[PathType, TimeSeries]

    def atoms(self) -> Iterable[Atom]:
        pass

    def add(self, other: Node) -> Trace:
        pass

    def __iadd__(self, other: Node) -> Trace:
        pass

    def update(self, other: Union[Monitor, Trace]) -> None:
        raise NotImplementedError()

    def __ior__(self, other: Union[Monitor, Trace]) -> Trace:
        pass

    def __or__(self, other: Union[Monitor, Trace]) -> Trace:
        pass

    @classmethod
    def _extract_properties(
            cls, element: Any, prefix: PathType = ()
    ) -> Iterable[Tuple[PathType, Any]]:
        """Convert nested structure into flat list with tuple capturing nested paths."""
        if isinstance(element, dict):
            return funcy.cat(
                cls._extract_properties(v, prefix + (k,)) for k, v in element.items()
            )
        if isinstance(element, list):
            return funcy.cat(
                cls._extract_properties(v, prefix + (str(i),))
                for i, v in enumerate(element)
            )
        return [(prefix, element)]

    def _record(
            self, element: Any, timestamp: Callable[[Any], int]
    ) -> None:
        time = timestamp(element)
        if time is None:
            return
        for path, value in self._extract_properties(element):
            path @= (time, value)

    def record(
            self, element: Any, *, timestamp: Callable[[Mapping], int]
    ) -> None:
        if isinstance(element, dict):
            self._record(element, timestamp)
        else:
            for e in element:
                self.record(e, timestamp=timestamp)

    def evaluate(
            self, phi: Union[Node], at: Any = False
    ) -> Optional[bool]:
        pass

