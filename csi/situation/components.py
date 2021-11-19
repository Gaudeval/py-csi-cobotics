"""
Core definition of situations and their components.

Components are the build block of situations, capturing individual properties
of the system. They can be composed to define complex situations and the scope
of said system.

As an example a situation where the operator is close to an active welder can
be built upon the distance between the operator and the welder, and the active
status of the welder.
"""
import typing
from typing import Tuple

import attr
import lenses
from mtfl import AtomicPred, And, G, WeakUntil, Implies, Neg, Next
from mtfl.ast import Or, Lt, Eq

Atom = AtomicPred
Node = typing.Union[AtomicPred, And, Or, Lt, Eq, G, WeakUntil, Implies, Neg, Next]


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


PathType = Tuple[str]