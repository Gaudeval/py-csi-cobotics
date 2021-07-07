import abc
import itertools
import math
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
)

import attr
from traces import TimeSeries

from csi.monitor import Trace

D = TypeVar("D", int, float)


# TODO Record out of domain value as None in coverage record
# TODO Only count entries where no value is None as covered
# TODO Add wrapper for transition/combination of domain coverage
# TODO Add method to highlight missing values in coverage


class DomainDefinition(abc.ABC):
    @abc.abstractmethod
    def value_of(self, v) -> Optional[Any]:
        return None

    @abc.abstractmethod
    def __len__(self) -> int:
        return 0


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


# FIXME Combinations field only valid for transition domains if coming from a projection with a single transition domain
class EventCombinationsRegistry:
    domain: Dict[str, Domain]
    default: Dict[str, Any]
    combinations: Set[FrozenSet[Tuple[Tuple[str, ...], Any]]]
    per_transitions: Dict[str, Any]

    def __init__(self):
        self.domain = {}
        self.default = defaultdict()
        self.combinations = set()
        self.per_transitions = defaultdict(set)

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
        projection.per_transitions = {
            e: {
                frozenset((k, v) for k, v in c if k in keys)
                for c in self.per_transitions[e]
            }
            for e in self.per_transitions
            if e in keys
        }
        if (
            len([d for e, d in self.domain.items() if e in keys and d.on_transition])
            == 1
        ):
            k = next(
                iter(
                    e for e in self.domain if e in keys and self.domain[e].on_transition
                )
            )
            projection.combinations = projection.per_transitions[k]
        return projection

    def merge(self, other):
        # TODO check domain and fill gaps
        # TODO Create new registry containing merged domains/defaults/values
        assert self.domain == other.domain
        self.combinations.update(other.combinations)

    def restrict(self):
        # TODO restrict domain of a specific variable
        raise NotImplementedError

    def register(self, trace: Trace):
        event_keys = sorted(self.domain)
        events = TimeSeries.merge([trace.values[e.id] for e in event_keys])
        events.compact()
        # TODO Fill gaps in missing values
        # TODO Configure behaviour on unknown values
        previous_state = {}
        for _, v in events.items():
            entry = set()
            for (e, d), i in zip(sorted(self.domain.items()), v):
                entry.add((e, i if i in d else None))
            self.combinations.add(frozenset(entry))


#            # TODO if all(i in self.domain[e].scalars for e, i in zip(event_keys, v)):
#            # Compute transition pair values
#            transitions = {}
#            for e, i in zip(event_keys, v):
#                if self.domain[e].on_transition:
#                    if e in previous_state and previous_state[e] != i:
#                        transitions[e] = (previous_state[e], i)
#                previous_state[e] = i
#            # Combine each transition with all other values
#            for c, t in transitions.items():
#                self.per_transitions[c].add(
#                    frozenset((e, i if e != c else t) for e, i in zip(event_keys, v))
#                )


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
