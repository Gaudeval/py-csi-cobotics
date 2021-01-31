import attr
from typing import TypeVar

from mtl.ast import AtomicPred, And, Or, Lt, Eq, G, WeakUntil, Implies, Neg, Next

Atom = AtomicPred

Node = TypeVar("Node", AtomicPred, And, Or, Lt, Eq, G, WeakUntil, Implies, Neg, Next)


@attr.s(frozen=True, auto_attribs=True, slots=True, hash=True)
class SafetyCondition:
    uid: str
    condition: Node
