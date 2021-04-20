from functools import reduce
from operator import mul
from collections import defaultdict
from typing import Mapping, FrozenSet, Any, Tuple, Set

from traces import TimeSeries

from csi.monitor import Trace


class EventCombinationsRegistry:
    domain: Mapping[str, FrozenSet[Any]]
    default: Mapping[str, FrozenSet[Any]]
    combinations: Set[FrozenSet[Tuple[str, Any]]]

    def __init__(self):
        self.domain = {}
        self.default = defaultdict()
        self.combinations = set()

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
        self.combinations.update(other.domain)

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
