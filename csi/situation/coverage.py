"""
Definition and calculation of coverage metrics and coverage-related helpers.

"""
from collections import defaultdict
from functools import reduce
from operator import mul
from typing import Dict, Any, Set, FrozenSet, Tuple

from traces import TimeSeries

from csi.situation.components import _Atom
from csi.situation.domain import Domain
from csi.situation.monitoring import Trace


# TODO Add method to Domain to register new atom, its domain, and default value
# TODO Add parameters/configuration to clarify behaviour on out of domain value
class EventCombinationsRegistry:
    domain: Dict[_Atom, Domain]
    default: Dict[_Atom, Any]
    # TODO Rename to clarify field captures encountered values
    combinations: Set[FrozenSet[Tuple[_Atom, Any]]]

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
        if self.domain == other.domain:
            self.combinations.update(other.combinations)
        else:
            # TODO Get all values for the other, project into current
            raise NotImplementedError()

    def record(self, values: Dict[_Atom, Any]):
        entry = {(k, v) for k, v in values.items() if k in self.domain}
        undefined = {(k, None) for k in self.domain if k not in values}
        self.combinations.add(frozenset(entry | undefined))

    def restrict(self, restrictions: Dict[_Atom, Domain]):
        """Restrict domain of a specific variable"""
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
        # FIXME Key sorting relies on id field being present, not the case for non Atom keys
        event_keys = sorted(
            self.domain,
            key=lambda d: getattr(d, "id", (str(d),)),
        )
        events = TimeSeries.merge(
            [trace.values[getattr(e, "id", e)] for e in event_keys]
        )
        events.compact()
        for _, v in events.items():
            entry = set()
            for (e, d), i in zip(
                sorted(
                    self.domain.items(),
                    key=lambda d: getattr(d[0], "id", (str(d[0]),)),
                ),
                v,
            ):
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
