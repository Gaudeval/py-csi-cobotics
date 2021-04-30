from csi.monitor import G, implies, F, until, weak_until, Monitor, Trace, timed_until
from csi.safety import SafetyCondition

from .monitor import SafetyControllerStatus, Loc, Act, RngDet, Phase, SafMod

SafCtr = SafetyControllerStatus

HSe = (
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
    & (SafCtr.rngDet.eq(RngDet.near) | SafCtr.rngDet.eq(RngDet.close))
)

HCe = (
    (
        SafCtr.safmod.eq(SafMod.normal)
        | SafCtr.safmod.eq(SafMod.hguid)
        | SafCtr.safmod.eq(SafMod.ssmon)
        | SafCtr.safmod.eq(SafMod.pflim)
    )
    & (
        SafCtr.hsp.eq(Phase.act)
        | SafCtr.hsp.eq(Phase.mit1)
        | SafCtr.hsp.eq(Phase.mit2)
        | SafCtr.hsp.eq(Phase.mit)
        | SafCtr.hsp.eq(Phase.res)
    )
    & (SafCtr.ract.eq(Act.welding) & SafCtr.wact.eq(Act.welding))
    & (SafCtr.rngDet.eq(RngDet.close))
)

HRWe = (
    (
        SafCtr.safmod.eq(SafMod.normal)
        | SafCtr.safmod.eq(SafMod.hguid)
        | SafCtr.safmod.eq(SafMod.ssmon)
        | SafCtr.safmod.eq(SafMod.pflim)
    )
    & (SafCtr.rloc.eq(Loc.sharedTbl))
    & SafCtr.lgtBar
)

predicates = [
    SafetyCondition(
        "Final:Tbl",
        F(~SafCtr.otab),
    ),
    SafetyCondition(
        "Final:Cell",
        F(SafCtr.oloc.eq(None)),
    ),
    SafetyCondition(
        "HS:detected",
        G(
            implies(
                (HSe & SafCtr.hsp.eq(Phase.inact)),
                timed_until(HSe, SafCtr.hsp.eq(Phase.act), lo=0.0, hi=0.5),
            )
        ),
    ),
    SafetyCondition(
        "HS:mitigated",
        G(implies(SafCtr.hsp.eq(Phase.act), F(SafCtr.hsp.eq(Phase.mit)))),
    ),
    SafetyCondition(
        "HS:handled",
        G(implies(SafCtr.hsp.eq(Phase.mit), F(SafCtr.hsp.eq(Phase.inact)))),
    ),
    SafetyCondition(
        "HS:not_mis",
        G(~SafCtr.hsp.eq(Phase.mis)),
    ),
    SafetyCondition(
        "HC:detected",
        G(
            implies(
                (HCe & SafCtr.hcp.eq(Phase.inact)),
                timed_until(HCe, SafCtr.hcp.eq(Phase.act), lo=0.0, hi=0.5),
            )
        ),
    ),
    SafetyCondition(
        "HC:mitigated",
        G(implies(SafCtr.hcp.eq(Phase.act), F(SafCtr.hcp.eq(Phase.mit)))),
    ),
    SafetyCondition(
        "HC:handled",
        G(implies(SafCtr.hcp.eq(Phase.mit), F(SafCtr.hcp.eq(Phase.inact)))),
    ),
    SafetyCondition(
        "HC:not_mis",
        G(~SafCtr.hcp.eq(Phase.mis)),
    ),
    SafetyCondition(
        "HRW:detected",
        G(
            implies(
                (HRWe & SafCtr.hrwp.eq(Phase.inact)),
                timed_until(HRWe, SafCtr.hrwp.eq(Phase.act), lo=0.0, hi=0.5),
            )
        ),
    ),
    SafetyCondition(
        "HRW:mitigated",
        G(implies(SafCtr.hrwp.eq(Phase.act), F(SafCtr.hrwp.eq(Phase.mit)))),
    ),
    SafetyCondition(
        "HRW:handled",
        G(implies(SafCtr.hrwp.eq(Phase.mit), F(SafCtr.hrwp.eq(Phase.inact)))),
    ),
    SafetyCondition(
        "HRW:not_mis",
        G(~SafCtr.hrwp.eq(Phase.mis)),
    ),
]
