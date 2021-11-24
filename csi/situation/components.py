"""
Core definition of situations and their components.

Components are the build block of situations, capturing individual properties
of the system. They can be composed to define complex situations and the scope
of said system.

As an example a situation where the operator is close to an active welder can
be built upon the distance between the operator and the welder, and the active
status of the welder.
"""
from __future__ import annotations
from typing import Optional, Tuple, Union, Set, TypeVar, Type, overload

import attr
import lenses
from mtfl import AtomicPred, And, G, WeakUntil, Implies, Neg, Next
from mtfl.ast import Or, Lt, Eq

from csi.situation.domain import Domain

PathType = Tuple[str, ...]

C = TypeVar("C", bound="Context")


@attr.s(frozen=True, auto_attribs=True, repr=False, slots=True, order=False, init=False)
class _Atom(AtomicPred):
    """A single component used in the definition of a situation"""
    path: PathType
    domain: Domain

    def __init__(self, path, domain=None):
        object.__setattr__(self, "path", path)
        object.__setattr__(self, "domain", domain)
        super(_Atom, self).__init__("::".join(path))

    def __str__(self):
        return "::".join(self.path)


# TODO Check for duplicate definition
Node = Union[_Atom, And, Or, Lt, Eq, G, WeakUntil, Implies, Neg, Next]


@attr.s(frozen=True, repr=True, eq=True, order=True, hash=True)
class Context:
    """Acts as a namespace to organise atoms"""
    _name: str = attr.ib(factory=str)
    _path: PathType = attr.ib(factory=tuple)

    def __set_name__(self, owner: Type[Context], name: str) -> None:
        object.__setattr__(self, "_name", name)

    @overload
    def __get__(self: C, instance: None, owner: None) -> C:
        ...

    @overload
    def __get__(self: C, instance: Context, owner: Type[Context]) -> C:
        # instance could really be an object and owner is an Type[object]
        ...

    def __get__(self: C, instance: Context | None, owner: Type[Context] | None) -> C:
        if instance is None:
            return attr.evolve(self, path=(self._name,))
        return attr.evolve(self, path=instance._path + (self._name,))


@attr.s(frozen=True, repr=True, eq=True, order=True, hash=True)
class Alias:
    """Defines a situation within a specific context"""
    condition: Node = attr.ib()

    def __get__(self, instance: Context | None, owner: Type[Context] | None) -> Node:
        if instance is None:
            path = tuple()
        else:
            path = instance._path
        atoms = set(lenses.bind(self.condition.walk()).Each().Instance(_Atom).collect())
        v = {a.id: _Atom(path + a.path, a.domain) for a in atoms}
        return self.condition[v]


@attr.s(frozen=True, repr=True, eq=True, order=True, hash=True)
class Component:
    """Defines a component in its context"""
    domain: Optional[Domain] = attr.ib(default=None)
    _name: str = attr.ib(factory=str)

    def __set_name__(self, owner: Type[Context], name: str) -> None:
        object.__setattr__(self, "_name", name)

    @overload
    def __get__(self, instance: None, owner: None) -> _Atom:
        ...

    @overload
    def __get__(self, instance: Context, owner: Type[Context]) -> _Atom:
        ...

    def __get__(self, instance: Context | None, owner: Type[Context] | None) -> _Atom:
        if instance is None:
            return _Atom((self._name,), self.domain)
        return _Atom(instance._path + (self._name,), self.domain)
