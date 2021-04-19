from pathlib import Path

from csi.monitor import Monitor, Trace
from csi.twin import DigitalTwinRunner, DataBase
from csi.twin.importer import from_table

from .monitor import SafetyControllerStatus, Notif, Act, Loc, RngDet, SafMod, Phase


class SafetyDigitalTwinRunner(DigitalTwinRunner):

    safety_conditions = []

    def process_output(self):
        """Extract values from simulation message trace"""

        # Load database
        if not self.database_output.exists():
            raise FileNotFoundError(self.database_output)
        db = DataBase(self.database_output)

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
        trace[P.lgtBar] = (0.0, False)
        for m in from_table(db, "lightgatetrigger"):
            trace[P.lgtBar] = (m.timestamp, m.broken == 1)

        # rloc
        trace[P.rloc] = (0.0, Loc.inCell)
        trace[P.oloc] = (0.0, None)
        for m in from_table(db, "triggerregionenterevent"):
            if m.entity == "ur10-cobot":
                if m.region == "atWeldSpot":
                    trace[P.rloc] = (m.timestamp, Loc.atWeldSpot)
                if m.region == "sharedTbl":
                    trace[P.rloc] = (m.timestamp, Loc.sharedTbl)
            if m.entity == "Operator-Operator" and m.region == "inCell":
                trace[P.oloc] = (m.timestamp, Loc.inCell)
        for m in from_table(db, "triggerregionexitevent"):
            if m.entity == "ur10-cobot":
                if m.region == "atWeldSpot":
                    trace[P.rloc] = (m.timestamp, Loc.inCell)
                if m.region == "sharedTbl":
                    trace[P.rloc] = (m.timestamp, Loc.inCell)
            if m.entity == "Operator-Operator" and m.region == "inCell":
                trace[P.oloc] = (m.timestamp, None)

        # HCp, HSp, HRWp
        trace[P.hcp] = (0.0, Phase.inact)
        trace[P.hsp] = (0.0, Phase.inact)
        trace[P.hrwp] = (0.0, Phase.inact)
        for m in from_table(db, "safetyphasemessage"):
            if m.hazard == "HCp":
                trace[P.hcp] = (m.timestamp, Phase(m.status))
            if m.hazard == "HSp":
                trace[P.hsp] = (m.timestamp, Phase(m.status))
            if m.hazard == "HRWp":
                trace[P.hrwp] = (m.timestamp, Phase(m.status))
            # trace[getattr(P, m.hazard.lower())] = (m.timestamp, Phase(m.status))

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

        return trace, self.safety_conditions


if __name__ == "__main__":
    SafetyDigitalTwinRunner.process_output(
        Path("../build/Unity_Data/StreamingAssets/CSI/Databases/messages.safety.db")
    )
