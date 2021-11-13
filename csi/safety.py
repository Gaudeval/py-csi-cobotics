"""
A definition of safety-related conditions and their components.
"""
import typing
import attr

from mtfl.ast import AtomicPred, And, Or, Lt, Eq, G, WeakUntil, Implies, Neg, Next

Atom = AtomicPred

Node = typing.Union[AtomicPred, And, Or, Lt, Eq, G, WeakUntil, Implies, Neg, Next]


@attr.s(frozen=True, auto_attribs=True, slots=True, hash=True)
class SafetyCondition:
    """Uniquely identified safety condition and identifying MTL condition"""

    uid: str
    condition: Node


@attr.s(frozen=True, auto_attribs=True, slots=True, hash=True)
class UnsafeControlAction(SafetyCondition):
    """STPA Unsafe Control Action definition"""

    description: str


@attr.s(frozen=True, auto_attribs=True, slots=True, hash=True)
class Hazard(SafetyCondition):
    """STPA Hazard definition"""

    description: str
