"""Define monitor trace format for safety controller evaluation."""
from enum import Enum

from csi.monitor import Context, Term, Trace


class Act(Enum):
    welding = 0
    idle = 1
    exchWrkp = 2
    off = 3


class Notif(Enum):
    leaveArea = 0
    ok = 1


class Loc(Enum):
    atTable = 0
    sharedTbl = 1
    inCell = 2
    atWeldSpot = 3


class SafMod(Enum):
    pflim = 0
    normal = 1
    stopped = 2
    srmst = 3
    ssmon = 4
    hguid = 5


class RngDet(Enum):
    far = 0
    near = 1
    close = 2


class SafetyControllerStatus(Context):
    """Safety controller status variables"""

    notif = Term()
    ract = Term()
    lgtBar = Term()
    rloc = Term()
    wact = Term()
    safmod = Term()
    notif_leaveWrkb = Term()
    rngDet = Term()


# class Robot(Context):
# pass

if __name__ == "__main__":
    P = SafetyControllerStatus()
    trace = Trace()

    trace[P.notif] = (0, Notif.leaveArea)
    trace[P.ract] = (0, Act.exchWrkp)
    trace[P.lgtBar] = (0, True)
    trace[P.rloc] = (0, Loc.atTable)
    trace[P.wact] = (0, Act.welding)
    trace[P.safmod] = (0, SafMod.hguid)
    trace[P.notif_leaveWrkb] = (0, True)
    trace[P.rngDet] = (0.0, RngDet.far)