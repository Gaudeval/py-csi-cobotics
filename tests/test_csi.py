from csi.twin import DBMessageImporter
from csi.monitor import Trace
from csi.twin.orm import DataBase
from scenarios.tcx.safety.hazards import hazard_monitor, hazards
from tests.test_monitor import Monitor, World


class TestCsi:
    def test_main(self):
        P = World()
        print("-- Predicates -----")
        w = Monitor()
        w |= hazard_monitor

        print("-- Rules -----")
        for r in w.atoms():
            print(r)

        print("-- Messages -----")
        db = DataBase("./fixtures/csi-large.db")
        for element in sorted(db.messages(), key=lambda m: m["unix_toi"]):
            print(dict(element.items()))

        print(".. Values .....")
        message_trace = Trace()
        message_importer = DBMessageImporter()
        message_importer.import_messages(message_trace, db)
        for k, v in message_trace.values.items():
            print("\t", k, list(i for i in v.items()))

        print(".. Predicates .....")
        for k, v in message_trace.values.items():
            print("\t", k, list(i for i in v.items()))

        print(".. Hazards .....")
        for h in hazards:
            print("{} -".format(h.uid), h.description)
            print("\t", w.evaluate(message_trace, h.condition))

        print(".. Missing .....")
        for p in sorted(w.atoms() - message_trace.atoms()):
            print("\t", ".".join(p.id))

        assert True
