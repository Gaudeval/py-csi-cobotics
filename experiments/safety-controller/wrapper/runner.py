from pathlib import Path

from csi.monitor import Monitor, Trace
from csi.twin import BuildRunner, DataBase
from csi.twin.importer import from_table

from monitor import SafetyControllerStatus, Notif, Act, Loc, RngDet, SafMod


class SafetyBuildRunner(BuildRunner):
    @classmethod
    def process_output(cls, database_path, safety_conditions=None):
        """Extract values from simulation message trace"""

        # Load database
        if not Path(database_path).exists():
            raise FileNotFoundError(database_path)
        db = DataBase(database_path)

        # Prepare trace
        trace = Trace()
        P = SafetyControllerStatus()

        # notif
        trace[P.notif] = (0.0, Notif.ok)
        for m in from_table(db, "operatorinteraction"):
            trace[P.notif] = (m.timestamp, Notif(m.status))

        # ract / wact
        trace[P.ract] = (0.0, Act.idle)
        trace[P.wact] = (0.0, Act.idle)
        for m in from_table(db, "actstatus"):
            s = Act(m.status)
            if m.topic == "cobot/mode/update":
                trace[P.ract] = (m.timestamp, s)
            elif m.topic == "welder/mode/update":
                trace[P.wact] = (m.timestamp, s)

        # lgtBar
        trace[P.wact] = (0.0, False)
        for m in from_table(db, "lightgatetrigger"):
            trace[P.lgtBar] = (m.timestamp, m.broken == 1)

        # rloc
        trace[P.rloc] = (0.0, Loc.inCell)
        for m in from_table(db, "triggerregionenterevent"):
            if m.entity == "ur10-cobot":
                if m.region == "atWeldSpot":
                    trace[P.rloc] = (m.timestamp, Loc.atWeldSpot)
                if m.region == "sharedTbl":
                    trace[P.rloc] = (m.timestamp, Loc.sharedTbl)
        for m in from_table(db, "triggerregionexitevent"):
            if m.entity == "ur10-cobot":
                if m.region == "atWeldSpot":
                    trace[P.rloc] = (m.timestamp, Loc.inCell)
                if m.region == "sharedTbl":
                    trace[P.rloc] = (m.timestamp, Loc.inCell)

        # safmod
        trace[P.safmod] = (0.0, SafMod.normal)
        for m in from_table(db, "safetymoderequest"):
            raise NotImplementedError

        # notif_leaveWrkb
        trace[P.notif_leaveWrkb] = (0.0, False)
        for m in from_table(db, "operatorworkbenchinteraction"):
            trace[P.notif_leaveWrkb] = (m.timestamp, m.status == 1)

        # rngDet
        trace[P.rngDet] = (0.0, RngDet.far)
        for m in from_table(db, "distancemeasurement"):
            if m.distance < 1.0:
                trace[P.rngDet] = (m.timestamp, RngDet.close)
            elif m.distance < 2.0:
                trace[P.rngDet] = (m.timestamp, RngDet.near)
            else:
                trace[P.rngDet] = (m.timestamp, RngDet.far)

        return trace, safety_conditions


if __name__ == "__main__":
    SafetyBuildRunner.process_output(
        Path("../build/Unity_Data/StreamingAssets/CSI/Databases/messages.safety.db")
    )
