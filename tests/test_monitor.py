import enum
import mtl

from pprint import pprint

import pytest

from csi.monitor import Context, Monitor, Trace, Term


class Constraint(Context):
    maximum_height = Term()


class Operator(Context):
    has_component = Term()
    height = Term()
    position = Term()


class World(Context):
    operator = Operator()
    constraint = Constraint()
    props = Operator()
    height = Term()
    speed = Term()
    position = Term()


class TestMonitor:
    def test_output(self):
        P = World()
        w = Monitor()

        print("== Predicates test =====")
        w += ~P.operator.has_component
        w += P.operator.has_component
        w += ~P.operator.has_component

        w += P.operator.height.eq(5)
        w += P.operator.height < 42
        w += P.operator.height <= 42
        w += P.operator.height > 42
        w += P.operator.height >= 42

        w += P.operator.height.eq(P.constraint.maximum_height)
        w += P.operator.height < P.constraint.maximum_height

        w += (P.operator.height > 5) & (P.operator.height < P.constraint.maximum_height)

        assert len({P.operator.height, P.operator.height}) == 1
        assert len({P.operator.height.eq(5), P.operator.height.eq(5)}) == 1

        pprint(w.atoms())

        print("== Trace insertion test =====")
        t = Trace()
        t[P.constraint.maximum_height] = (0, 30)
        t[P.operator.height] = (5, 42)
        t[P.operator.height] = (6, 5)
        t[P.operator.height] = (7, 30)
        t[P.constraint.maximum_height] = (8, 40)
        with pytest.raises(Exception):
            t[P.unknown] = (9, True)
        pprint({s: list(v.items()) for s, v in t.values.items()})

        print("== Trace eval test =====")
        print("-- Dummy -----")
        p = mtl.parse("dummy_predicate")
        print(p)
        print(w.evaluate(t, p))
        print("-- Op Height == 5 -----")
        print((P.operator.height.eq(5)))
        print(t.project({P.operator.height}))
        print(w.evaluate(t, P.operator.height.eq(5), time=None))

        print("== Enum predicates =====")

        class DummyEnum(enum.Enum):
            FOO = enum.auto()
            BAR = enum.auto()
            BAZ = enum.auto()

        n = ~(P.operator.position.eq(DummyEnum.FOO))
        f = P.operator.position.eq(DummyEnum.FOO)
        t[P.operator.position] = (0, DummyEnum.FOO)
        t[P.operator.position] = (10, DummyEnum.BAR)

        print(n)
        print(w.evaluate(t, n, time=None))
        print(f)
        print(w.evaluate(t, f, time=None))

        print("== Test comparisons =====")
        i = Monitor()
        j = Monitor()

        i += P.props.height.eq(5)
        j += P.props.height.eq(5)
        assert i == j

        i += P.props.height < 5
        assert i != j

        print(hash(i), i)
        print(hash(j), j)

        print("== Test merging =====")
        i = Monitor()
        j = Monitor()

        i += P.height.eq(5)
        j += P.height < 5
        print(i, j)
        assert (j | i).atoms() == j.atoms()

        j += P.height <= 5
        assert (j | i).atoms() == i.atoms()

        i += P.speed >= 4
        assert (j | i).atoms() == i.atoms()

        print("== Merge =====")
        u = Monitor()
        u += P.operator.height > 180

        v = Monitor()
        v += P.operator.position.eq(DummyEnum.FOO)

        w = Monitor()
        w += P.operator.position.eq(DummyEnum.FOO)
        w += P.operator.height < 170

        print(w.atoms())
        print((v | w).atoms())
        print((w | v).atoms())
        print((u | v).atoms())

        s = Trace()
        s[P.operator.height] = (0, 170)
        s[P.operator.height] = (1, 160)

        print("s:", {n: list(v) for n, v in s.values.items()})

        t = Trace()
        t[P.position] = (0, DummyEnum.BAR)
        t[P.operator.height] = (0, 210)
        t[P.position] = (5, DummyEnum.BAZ)
        t[P.position] = (9, DummyEnum.FOO)

        print("t:", t.values)
        print("s|t:", list((s | t).values[("operator", "height")].items()))
        print("t|s:", list((t | s).values[("operator", "height")].items()))

        print("== Out-of-order updates =====")
        w = Monitor()
        w += P.operator.height < 170

        t = Trace()
        t[P.operator.height] = (0, 210)
        t[P.operator.height] = (10, 160)
        t[P.operator.height] = (50, 200)
        t[P.operator.height] = (25, 42)
        t[P.operator.height] = (5, 10)

        print(list(t.values[("operator", "height")].items()))

        print("== Overlapping updates =====")
        t = Trace()
        t[P.operator.height] = (0, 210)
        t[P.operator.height] = (5, 10)
        t[P.operator.height] = (10, 160)
        t[P.operator.height] = (25, 42)
        t[P.operator.height] = (50, 200)
        print(
            list(
                t.values[
                    (
                        "operator",
                        "height",
                    )
                ].items()
            )
        )

        t[P.height] = (0, 100)
        t[P.height] = (11, 161)
        t[P.height] = (49, 40)
        t[P.height] = (50, 150)
        print(list(t.values[("height",)].items()))

        print(t)
