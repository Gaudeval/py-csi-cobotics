import attr
import enum

from csi.safety import SafetyCondition


class UCACause(enum.Enum):
    PROVIDING = enum.auto()
    NOT_PROVIDING = enum.auto()
    DURATION = enum.auto()
    SCHEDULING = enum.auto()


@attr.s(frozen=True, auto_attribs=True, slots=True, hash=True)
class UnsafeControlAction(SafetyCondition):
    description: str


@attr.s(frozen=True, auto_attribs=True, slots=True, hash=True)
class Hazard(SafetyCondition):
    description: str
