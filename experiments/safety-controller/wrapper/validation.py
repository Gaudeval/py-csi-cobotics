from csi.monitor import G, implies, F, until, weak_until, Monitor, Trace
from csi.safety import SafetyCondition

from .monitor import SafetyControllerStatus, Loc, Act, RngDet, Phase, SafMod

SafCtr = SafetyControllerStatus

predicates = [
    SafetyCondition(
        "HS:detected",
        G(
            implies(
                (
                    SafCtr.safmod.eq(SafMod.normal)
                    | SafCtr.safmod.eq(SafMod.hguid)
                    | SafCtr.safmod.eq(SafMod.ssmon)
                    | SafCtr.safmod.eq(SafMod.pflim)
                )
                & (
                    SafCtr.ract.eq(Act.exchWrkp)
                    | SafCtr.ract.eq(Act.welding)
                    | SafCtr.wact.eq(Act.welding)
                )
                & (SafCtr.rngDet.eq(RngDet.near) | SafCtr.rngDet.eq(RngDet.close)),
                F(SafCtr.hsp.eq(Phase.act)),
            )
        ),
    ),
    SafetyCondition(
        "HS:handled:1",
        G(implies(SafCtr.hsp.eq(Phase.act), F(SafCtr.hsp.eq(Phase.mit)))),
    ),
    SafetyCondition(
        "HS:handled:2",
        G(implies(SafCtr.hsp.eq(Phase.mit), F(SafCtr.hsp.eq(Phase.inact)))),
    ),
    SafetyCondition(
        "HS:handled:3",
        F(SafCtr.oloc.eq(None)),  # FIXME F (operator.position = final)
    ),
    SafetyCondition(
        "HS:handled:4",
        G(~SafCtr.hsp.eq(Phase.mis)),
    ),
]
