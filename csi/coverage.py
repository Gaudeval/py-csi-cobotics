import abc
import itertools
import functools
import math
import operator
from functools import reduce
from operator import mul
from collections import defaultdict
from typing import (
    Mapping,
    FrozenSet,
    Any,
    Tuple,
    Set,
    Iterable,
    Dict,
    TypeVar,
    Optional,
    Callable,
)

import attr
from traces import TimeSeries

from csi.monitor import Trace
from csi.safety import Atom

D = TypeVar("D", int, float)


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


@attr.s(frozen=True, init=True)
class RangeDomain(DomainDefinition):
    a: float = attr.ib()
    b: float = attr.ib()
    step: float = attr.ib()  # TODO Constrain step to be positive

    def value_of(self, v) -> Optional[Any]:
        if self.a <= v < self.b:
            return math.floor((v - self.a) / self.step) * self.step + self.a
        return None

    def __len__(self) -> int:
        if self.a <= self.b:
            return math.ceil((self.b - self.a) / self.step)
        return 0


@attr.s(frozen=True, init=True)
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


@attr.s(frozen=True, init=True)
class SetDomain(DomainDefinition):
    contents: FrozenSet[Any] = attr.ib(converter=frozenset)

    def __len__(self) -> int:
        return len(self.contents)

    def value_of(self, v) -> Optional[Any]:
        return v if v in self.contents else None


@attr.s(frozen=True, init=True)
class FilterDomain(DomainDefinition):
    _definition: DomainDefinition = attr.ib()
    _filter: Callable[
        [
            Any,
        ],
        bool,
    ] = attr.ib()
    _value: Any = attr.ib()

    @_definition.validator
    def _defined_domain(self, attribute, value):
        if not isinstance(value, DomainDefinition):
            raise ValueError()

    def __len__(self) -> int:
        if self._definition.value_of(self._value) is None:
            return len(self._definition) + 1
        else:
            return len(self._definition)

    def value_of(self, v) -> Optional[Any]:
        if self._definition.value_of(v) is None:
            if self._filter(v):
                return self._value
            else:
                return None
        else:
            return self._definition.value_of(v)


@attr.s(frozen=True, init=True)
class Domain:
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
    return Domain(SetDomain(values))


def domain_range(a: float, b: float, step: float):
    return Domain(RangeDomain(a, b, step))


def domain_linspace(a: float, b: float, count: float):
    return Domain(SpaceDomain(a, b, count))


def __le(a, b):
    return operator.le(a, b)


def __ge(a, b):
    return operator.ge(a, b)


def domain_threshold_range(
    a: float, b: float, step: float, upper: bool = False, lower: bool = False
):
    d = RangeDomain(a, b, step)
    if upper:
        d = FilterDomain(d, functools.partial(__ge, b=b), b)
    if lower:
        d = FilterDomain(d, functools.partial(__le, b=a), a)
    return Domain(d)


def domain_identity():
    return Domain(IdentityDomain())


# FIXME Combinations field only valid for transition domains if coming from a projection where a single transition domain is defined
class EventCombinationsRegistry:
    domain: Dict[Atom, Domain]
    default: Dict[Atom, Any]
    combinations: Set[FrozenSet[Tuple[Atom, Any]]]

    def __init__(self):
        self.domain = {}
        self.default = defaultdict()
        self.combinations = set()

    #    def values_of(self, k):
    #        yield from zip(itertools.repeat(k), self.domain[k].values)
    #
    #    def all_values(self) -> Iterable[FrozenSet[Tuple[str, Any]]]:
    #        yield from map(
    #            frozenset, itertools.product(*[self.values_of(k) for k in self.domain])
    #        )
    #
    #    def missing_values(self):
    #        yield from (x for x in self.all_values() if x not in self.combinations)

    @property
    def covered(self) -> int:
        return sum(1 for c in self.combinations if all(v is not None for _, v in c))

    @property
    def total(self) -> int:
        return reduce(mul, map(len, self.domain.values()), 1)

    @property
    def coverage(self) -> float:
        return float(self.covered) / self.total

    def project(self, keys):
        projection = EventCombinationsRegistry()
        projection.domain |= {k: v for k, v in self.domain.items() if k in keys}
        projection.default |= {k: v for k, v in self.default.items() if k in keys}
        projection.combinations = {
            frozenset((k, v) for k, v in c if k in keys) for c in self.combinations
        }
        return projection

    def merge(self, other):
        # TODO check domain and fill gaps
        # TODO Create new registry containing merged domains/defaults/values
        assert self.domain == other.domain
        self.combinations.update(other.combinations)

    def record(self, values: Dict[Atom, Any]):
        entry = {(k, v) for k, v in values.items() if k in self.domain}
        undefined = {(k, None) for k in self.domain if k not in values}
        self.combinations.add(frozenset(entry | undefined))

    def restrict(self, restrictions: Dict[Atom, Domain]):
        """ Restrict domain of a specific variable """
        restriction = EventCombinationsRegistry()
        restriction.domain |= {
            k: restrictions.get(k, d) for k, d in self.domain.items()
        }
        restriction.default |= {k: v for k, v in self.default.items()}
        restriction.combinations = {
            frozenset((k, restrictions.get(k, self.domain[k]).value(v)) for k, v in c)
            for c in self.combinations
        }
        return restriction

    def register(self, trace: Trace):
        event_keys = sorted(self.domain, key=lambda d: d.id)
        events = TimeSeries.merge([trace.values[e.id] for e in event_keys])
        events.compact()
        for _, v in events.items():
            entry = set()
            for (e, d), i in zip(sorted(self.domain.items(), key=lambda d: d[0].id), v):
                entry.add((e, d.value(i)))
            self.combinations.add(frozenset(entry))


if __name__ == "__main__":
    e = EventCombinationsRegistry()
    e.domain["a"] = Domain({1, 2, 3})
    e.domain["b"] = Domain({"x", "y"})

    print(list(e.all_values()))
    e.combinations.add(frozenset([("a", 1), ("b", "x")]))
    print(list(e.missing_values()))

    e = EventCombinationsRegistry()
    e.domain["a"] = Domain({1, 2, 3}, True)
    e.domain["b"] = Domain({"x", "y"})

    t = Trace()
    t["a"] = (0, 1)
    t["a"] = (1, 2)
    t["a"] = (2, 3)
    t["a"] = (3, 1)
    t["a"] = (4, 3)
    t["a"] = (5, 2)
    t["b"] = (0, "y")
    t["b"] = (3, "x")
    e.register(t)
    print(e.combinations)

    print(e.domain["a"].count, e.domain["b"].count)
    print(list(e.all_values()))
    print(e.coverage)
