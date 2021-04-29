import itertools
from functools import reduce
from operator import mul
from collections import defaultdict
from typing import Mapping, FrozenSet, Any, Tuple, Set, Iterable, Dict

from traces import TimeSeries

from csi.monitor import Trace


class EventCombinationsRegistry:
    domain: Dict[str, FrozenSet[Any]]
    default: Dict[str, FrozenSet[Any]]
    combinations: Set[FrozenSet[Tuple[str, Any]]]

    def __init__(self):
        self.domain = {}
        self.default = defaultdict()
        self.combinations = set()

    def values_of(self, k):
        yield from ((k, v) for v in self.domain[k])

    def all_values(self) -> Iterable[FrozenSet[Tuple[str, Any]]]:
        yield from map(
            frozenset, itertools.product(*[self.values_of(k) for k in self.domain])
        )

    def missing_values(self):
        yield from (x for x in self.all_values() if x not in self.combinations)

    @property
    def covered(self) -> int:
        return len(self.combinations)

    @property
    def total(self) -> int:
        return reduce(mul, (len(d) for d in self.domain.values() if len(d) > 0), 1)

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

    def restrict(self):
        # TODO restrict domain of a specific variable
        raise NotImplementedError

    def register(self, trace: Trace):
        event_keys = sorted(self.domain)
        events = TimeSeries.merge([trace.values[e] for e in event_keys])
        events.compact()
        # TODO Fill gaps in missing values
        # TODO Configure behaviour on unknown values
        for _, v in events.items():
            if all(i in self.domain[e] for e, i in zip(event_keys, v)):
                self.combinations.add(frozenset(zip(event_keys, v)))


if __name__ == "__main__":
    e = EventCombinationsRegistry()
    e.domain["a"] = frozenset({1, 2, 3})
    e.domain["b"] = frozenset({"x", "y"})

    print(list(e.all_values()))
    e.combinations.add(frozenset([("a", 1), ("b", "x")]))
    print(list(e.missing_values()))
