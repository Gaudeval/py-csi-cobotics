"""
Definition of situation elements' domain for coverage.

The domain of a situation element captures its range of values expected to be
observed in the system. The domain definition can capture the exact set of
values, intervals, or a mapping between observations and coverage requirements.

TODO Example of boolean domain

TODO Example of interval domain (distance)

TODO Example mapping domain ()
"""
import abc
import math
from typing import Optional, Any, FrozenSet, Iterable

import attr

# TODO Add wrapper for transition/combination of domain coverage
# TODO Add method to highlight missing values in coverage


class DomainDefinition(abc.ABC):
    @abc.abstractmethod
    def value_of(self, v) -> Optional[Any]:
        return None

    @abc.abstractmethod
    def __len__(self) -> int:
        return 0


class IdentityDomain(DomainDefinition):
    def value_of(self, v) -> Optional[Any]:
        return v

    def __len__(self) -> int:
        raise ValueError()


@attr.s(frozen=True, init=True, eq=True)
class RangeDomain(DomainDefinition):
    a: float = attr.ib()
    b: float = attr.ib()
    step: float = attr.ib()  # TODO Constrain step to be positive
    upper_bound: bool = attr.ib(default=False)
    lower_bound: bool = attr.ib(default=False)

    def value_of(self, v) -> Optional[Any]:
        if self.lower_bound and v < self.a:
            return self.a
        elif self.upper_bound and self.b <= v:
            return self.b
        elif self.a <= v < self.b:
            return math.floor((v - self.a) / self.step) * self.step + self.a
        return None

    def __len__(self) -> int:
        if self.a <= self.b:
            if self.upper_bound:
                return math.ceil((self.b - self.a) / self.step) + 1
            return math.ceil((self.b - self.a) / self.step)
        return 0


@attr.s(frozen=True, init=True, eq=True)
class SpaceDomain(DomainDefinition):
    a: float = attr.ib()
    b: float = attr.ib()
    count: float = attr.ib()  # TODO Constraint count to be strictly positive

    def __len__(self) -> int:
        return self.count

    def value_of(self, v) -> Optional[Any]:
        if self.a <= v < self.b:
            return (
                math.floor((v - self.a) * self.count / (self.b - self.a))
                * (self.b - self.a)
                / self.count
            )
        return None


@attr.s(frozen=True, init=True, eq=True)
class SetDomain(DomainDefinition):
    contents: FrozenSet[Any] = attr.ib(converter=frozenset)

    def __len__(self) -> int:
        return len(self.contents)

    def value_of(self, v) -> Optional[Any]:
        return v if v in self.contents else None


# TODO Rename to AtomDomain
@attr.s(frozen=True, init=True)
class Domain:
    """Domain of values for a component.

    A domain captures the possible values for a component. To support range of
    values, different values in the same range might be converted to a single
    one, unique to the range itself. A domain thus only requires to define
    such a conversion operation, and a length if applicable.

    None identifies out of scope values (as a value, or a range identifier).
    """

    _definition: DomainDefinition = attr.ib()

    @_definition.validator
    def _defined_domain(self, attribute, value):
        if not isinstance(value, DomainDefinition):
            raise ValueError()

    def __contains__(self, v) -> bool:
        return self.value(v) is not None

    def value(self, v):
        return self._definition.value_of(v)

    def __len__(self):
        return len(self._definition)


def domain_values(values: Iterable[Any]) -> Domain:
    """Define a domain from the exact set of possible values"""
    return Domain(SetDomain(values))


def domain_range(a: float, b: float, step: float):
    """Define a domain partitioned into ranges of size step in [a;b)"""
    return Domain(RangeDomain(a, b, step))


def domain_linspace(a: float, b: float, count: float):
    """Define a domain partitioned into count ranges in [a;b)"""
    return Domain(SpaceDomain(a, b, count))


def domain_threshold_range(
    a: float, b: float, step: float, upper: bool = False, lower: bool = False
):
    """Define a range domain including upper or lower values outside [a, b)"""
    d = RangeDomain(a, b, step, lower_bound=lower, upper_bound=upper)
    return Domain(d)


def domain_identity():
    """Define the identity domain containing all values"""
    return Domain(IdentityDomain())
