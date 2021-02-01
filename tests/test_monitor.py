import enum
import mtl

from pprint import pprint
from csi.monitor import Monitor, P, Trace


class TestMonitor:
    def test_output(self):
        w = Monitor()

        print("== Predicates test =====")
        w += ~P.operator.has_component
        w += P.operator.has_component
        w += ~P.operator.has_component

        w += P.operator.height == 5
        w += P.operator.height < 42
        w += P.operator.height <= 42
        w += P.operator.height > 42
        w += P.operator.height >= 42

        w += P.operator.height == P.constraint.maximum_height
        w += P.operator.height < P.constraint.maximum_height

        w += (P.operator.height > 5) & (P.operator.height < P.constraint.maximum_height)

        assert len({P.operator.height, P.operator.height}) == 1
        print((P.operator.height == 5) == (P.operator.height == 5))
        assert len({P.operator.height == 5, P.operator.height == 5}) == 1

        pprint(w.predicates)
        pprint(w.terms())

        print("== Trace insertion test =====")
        t = Trace(w)
        t.terms.constraint.maximum_height @= (0, 30)
        t.terms.operator.height @= (5, 42)
        t.terms.operator.height @= (6, 5)
        t.terms.operator.height @= (7, 30)
        t.terms.constraint.maximum_height @= (8, 40)
        t.terms.unknown @= (9, True)
        pprint({s: list(v.items()) for s, v in t.values.items()})

        print("== Trace eval test =====")
        print("-- Dummy -----")
        p = mtl.parse("dummy_predicate")
        print(p)
        print(t.evaluate(p))
        print("-- Op Height == 5 -----")
        print((P.operator.height == 5).as_mtl())
        print(t.evaluate((P.operator.height == 5)))

        print("== Enum predicates =====")

        class DummyEnum(enum.Enum):
            FOO = enum.auto()
            BAR = enum.auto()
            BAZ = enum.auto()

        n = P.operator.position != DummyEnum.FOO
        t += n
        f = P.operator.position == DummyEnum.FOO
        t += f
        t.terms.operator.position @= (0, DummyEnum.FOO)
        t.terms.operator.position @= (10, DummyEnum.BAR)

        print(n)
        print(t.evaluate(n, at=None))
        print(f)
        print(t.evaluate(f, at=None))

        print("== Test comparisons =====")
        i = Monitor()
        j = Monitor()

        i += P.props.height == 5
        j += P.props.height == 5
        print(i == j)

        i += P.props.height < 5
        print(i == j)

        print(hash(i), i)
        print(hash(j), j)

        print("== Test merging =====")
        i = Monitor()
        j = Monitor()

        i += P.height == 5
        j += P.height < 5
        print(i, j)
        print((j | i).predicates)

        j += P.height <= 5
        print((j | i).predicates)

        i += P.speed >= 4
        print((i | j).predicates)

        print("== Merge =====")
        u = Monitor()
        u += P.operator.height > 180

        v = Monitor()
        v += P.operator.position == DummyEnum.FOO

        w = Monitor()
        w += P.operator.position == DummyEnum.FOO
        w += P.operator.height < 170

        print(w.predicates)
        print((v | w).predicates)
        print((w | v).predicates)
        print((u | v).predicates)

        s = Trace(u)
        s.terms.operator.height @= (0, 170)
        s.terms.operator.height @= (1, 160)
        s.terms.operator.dummy @= (4, 42)

        print("s(rules):", [str(r) for r in s.ruleset.predicates])
        print("s:", {n: list(v) for n, v in s.values.items()})
        print("s:", {n: list(v) for n, v in s.mtl_predicates.items()})
        print("s|w:", {n: list(v) for n, v in (s | w).mtl_predicates.items()})

        t = Trace(v)
        t.terms.operator.position @= (0, DummyEnum.BAR)
        t.terms.operator.height @= (0, 210)
        t.terms.operator.position @= (5, DummyEnum.BAZ)
        t.terms.operator.position @= (9, DummyEnum.FOO)

        print("t:", t.values)
        print("t:", t.mtl_predicates)
        print("t|w:", (t | w).mtl_predicates)
        print("t|s:", (t | s).mtl_predicates)
        print("s|t:", (s | t).mtl_predicates)
        print("s|t:", list((s | t).values[("operator", "height")].items()))

        print("== Out-of-order updates =====")
        w = Monitor()
        w += P.operator.height < 170

        t = Trace(w)
        t.terms.operator.height @= (0, 210)
        t.terms.operator.height @= (10, 160)
        t.terms.operator.height @= (50, 200)
        t.terms.operator.height @= (25, 42)
        t.terms.operator.height @= (5, 10)

        print(list(t.values[("operator", "height")].items()))

        print("== Overlapping updates =====")
        w = Monitor()
        w += P.operator.height > P.max_height

        t = Trace(w)
        t.terms.operator.height @= (0, 210)
        t.terms.operator.height @= (5, 10)
        t.terms.operator.height @= (10, 160)
        t.terms.operator.height @= (25, 42)
        t.terms.operator.height @= (50, 200)
        print(list(t.values[("operator", "height")].items()))

        t.terms.max_height @= (0, 100)
        t.terms.max_height @= (11, 161)
        t.terms.max_height @= (49, 40)
        t.terms.max_height @= (50, 150)
        print(list(t.values[("max_height",)].items()))

        print(t.mtl_predicates)
