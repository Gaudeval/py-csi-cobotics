"""
A definition of safety-related conditions and their components.
"""
import attr

from csi.situation.components import Node


@attr.s(frozen=True, auto_attribs=True, slots=True, hash=True)
class SafetyCondition:
    """Uniquely identified safety condition and identifying MTL condition"""

    uid: str
    condition: Node


# TODO Remove if no usage is made and no distinction from Safety Condition
@attr.s(frozen=True, auto_attribs=True, slots=True, hash=True)
class UnsafeControlAction(SafetyCondition):
    """STPA Unsafe Control Action definition"""

    description: str


# TODO Remove if no usage is made and no distinction from Safety Condition
@attr.s(frozen=True, auto_attribs=True, slots=True, hash=True)
class Hazard(SafetyCondition):
    """STPA Hazard definition"""

    description: str
