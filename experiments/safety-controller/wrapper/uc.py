from typing import List, Tuple, Iterable

import attr

from csi.monitor import G, implies, F, until, weak_until, Monitor, Trace
from csi.safety import SafetyCondition

from .monitor import SafetyControllerStatus, Loc, Act, RngDet


@attr.s(frozen=True, auto_attribs=True, slots=True, hash=True)
class SafetyUseCase:
    name: str
    description: str
    conditions: List[SafetyCondition]
    coverage_criterions: List[Iterable[Tuple[str]]]

    def evaluate_conditions(self, trace: Trace) -> List[Tuple[bool, str]]:
        m = Monitor()
        return [(m.evaluate(trace, c.condition), c.uid) for c in self.conditions]

    def satisfies(self, trace: Trace) -> bool:
        return all(s for s, _ in self.evaluate_conditions(trace))


_P = SafetyControllerStatus()

_P.ractive = _P.ract.eq(Act.welding) | _P.ract.eq(Act.exchWrkp)
_P.ocell = _P.oloc.eq(Loc.inCell)


U1 = SafetyUseCase(
    "U1",
    "The operator walks to the welder during operation",
    [
        SafetyCondition(
            "U1_op_enters",
            F(_P.ocell & ~_P.otab),
        ),
        SafetyCondition(
            "U1_op_leaves",
            G(implies(_P.ocell & ~_P.otab, F(~_P.ocell))),
        ),
        SafetyCondition(
            "U1_robot_active",
            G(implies(F(_P.ocell), weak_until(_P.ractive, _P.ocell))),
        ),
        SafetyCondition(
            "U1_op_single_entry",
            G(implies(_P.ocell & ~_P.otab, until(_P.ocell, ~F(_P.ocell)))),
        ),
    ],
    [
        [_P.wact.id, _P.oloc.id],
        [_P.wact.id, _P.rngDet.id],
        [_P.rloc.id, _P.rngDet.id],
        [_P.rloc.id, _P.oloc.id],
        [_P.ract.id, _P.rngDet.id],
        [_P.ract.id, _P.oloc.id],
        [_P.notif.id],
        [_P.safmod.id],
    ],
)

U2 = SafetyUseCase(
    "U2",
    "The operator reaches across the workbench during operation",
    [
        SafetyCondition(
            "U2_op_enters",
            F(
                _P.otab
                & ~_P.lgtBar
                & ~_P.ocell
                & until(_P.otab & ~_P.lgtBar & ~_P.ocell, _P.otab & _P.lgtBar)
            ),
        ),
        SafetyCondition(
            "U2_op_leaves",
            G(implies(_P.otab & _P.lgtBar, F(~_P.lgtBar))),
        ),
        SafetyCondition(
            "U2_robot_active",
            G(implies(F(_P.lgtBar), weak_until(_P.ractive, _P.lgtBar))),
        ),
        SafetyCondition(
            "U2_op_single_entry",
            G(implies(_P.lgtBar, until(_P.lgtBar, ~F(_P.lgtBar)))),
        ),
    ],
    [
        [_P.wact.id, _P.lgtBar.id],
        [_P.rloc.id, _P.lgtBar.id],
        [_P.ract.id, _P.lgtBar.id],
        [_P.notif_leaveWrkb.id],
        [_P.safmod.id],
    ],
)

MU = SafetyUseCase(
    "MU",
    "The operator reaches the bench from behind the light curtain while standing out of reach of the range finder",
    [
        SafetyCondition(
            "MU_condition",
            F(
                _P.ocell
                & ~_P.otab
                & until(
                    _P.ocell & ~_P.otab, _P.ocell & _P.lgtBar & _P.rngDet.eq(RngDet.far)
                )
            ),
        )
    ],
    [],
)

if __name__ == "__main__":

    def _initialise_trace() -> Trace:
        t = Trace()
        t[_P.ract] = (0.0, Act.exchWrkp)
        t[_P.oloc] = (0.0, None)
        t[_P.otab] = (0.0, False)
        t[_P.lgtBar] = (0.0, False)
        t[_P.rngDet] = (0.0, RngDet.far)
        return t

    t = _initialise_trace()
    assert not U1.satisfies(t), U1.evaluate_conditions(t)
    assert not U2.satisfies(t), U2.evaluate_conditions(t)
    assert not MU.satisfies(t), MU.evaluate_conditions(t)

    t = _initialise_trace()
    t[_P.oloc] = (1.0, Loc.inCell)
    assert not U1.satisfies(t), U1.evaluate_conditions(t)
    assert not U2.satisfies(t), U2.evaluate_conditions(t)
    assert not MU.satisfies(t), MU.evaluate_conditions(t)

    t = _initialise_trace()
    t[_P.oloc] = (1.0, Loc.inCell)
    t[_P.oloc] = (2.0, None)
    assert U1.satisfies(t), U1.evaluate_conditions(t)
    assert not U2.satisfies(t), U2.evaluate_conditions(t)
    assert not MU.satisfies(t), MU.evaluate_conditions(t)

    t = _initialise_trace()
    t[_P.oloc] = (1.0, Loc.inCell)
    t[_P.ract] = (1.0, Act.idle)
    t[_P.oloc] = (2.0, None)
    t[_P.ract] = (2.0, Act.exchWrkp)
    assert U1.satisfies(t), U1.evaluate_conditions(t)
    assert not U2.satisfies(t), U2.evaluate_conditions(t)
    assert not MU.satisfies(t), MU.evaluate_conditions(t)

    t = _initialise_trace()
    t[_P.oloc] = (1.0, Loc.inCell)
    t[_P.ract] = (1.0, Act.idle)
    t[_P.oloc] = (2.0, None)
    assert not U1.satisfies(t), U1.evaluate_conditions(t)
    assert not U2.satisfies(t), MU.evaluate_conditions(t)
    assert not MU.satisfies(t), MU.evaluate_conditions(t)

    t = _initialise_trace()
    t[_P.oloc] = (1.0, Loc.inCell)
    t[_P.oloc] = (2.0, None)
    t[_P.oloc] = (3.0, Loc.inCell)
    t[_P.oloc] = (4.0, None)
    assert not U1.satisfies(t), U1.evaluate_conditions(t)
    assert not U2.satisfies(t), U2.evaluate_conditions(t)
    assert not MU.satisfies(t), MU.evaluate_conditions(t)

    t = _initialise_trace()
    t[_P.rngDet] = (0.0, RngDet.far)
    t[_P.oloc] = (1.0, Loc.inCell)
    t[_P.lgtBar] = (2.0, True)
    t[_P.lgtBar] = (3.0, False)
    t[_P.oloc] = (4.0, None)
    assert U1.satisfies(t), U1.evaluate_conditions(t)
    assert not U2.satisfies(t), U2.evaluate_conditions(t)
    assert MU.satisfies(t), MU.evaluate_conditions(t)

    t = _initialise_trace()
    t[_P.rngDet] = (0.0, RngDet.close)
    t[_P.oloc] = (1.0, Loc.inCell)
    t[_P.lgtBar] = (2.0, True)
    assert not U1.satisfies(t), U1.evaluate_conditions(t)
    assert not U2.satisfies(t), U2.evaluate_conditions(t)
    assert not MU.satisfies(t), MU.evaluate_conditions(t)

    t = _initialise_trace()
    t[_P.otab] = (0.0, True)
    t[_P.lgtBar] = (1.0, True)
    t[_P.oloc] = (1.1, Loc.inCell)
    t[_P.lgtBar] = (2.0, False)
    t[_P.oloc] = (2.0, None)
    assert not U1.satisfies(t), U1.evaluate_conditions(t)
    assert U2.satisfies(t), U2.evaluate_conditions(t)
    assert not MU.satisfies(t), MU.evaluate_conditions(t)

    t = _initialise_trace()
    t[_P.oloc] = (0.0, Loc.inCell)
    t[_P.lgtBar] = (1.0, True)
    t[_P.otab] = (1.0, True)
    t[_P.lgtBar] = (2.0, False)
    t[_P.otab] = (2.0, False)
    assert not U1.satisfies(t), U1.evaluate_conditions(t)
    assert not U2.satisfies(t), U2.evaluate_conditions(t)
    assert MU.satisfies(t), MU.evaluate_conditions(t)
