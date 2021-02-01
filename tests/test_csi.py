from csi.twin import DBMessageImporter
from csi.monitor import Trace
from csi.twin.orm import DataBase
from tests.test_monitor import Monitor, P
from scenarios import hazard_monitor, hazards


if __name__ == "__main__":
    print("-- Predicates -----")
    w = Monitor()
    w += P["test_device"].r.data > 0
    w |= hazard_monitor

    print("-- Rules -----")
    for r in w.predicates:
        print(r)

    print("-- Messages -----")
    db = DataBase("./fixtures/csi-large.db")
    for element in sorted(db.messages(), key=lambda m: m["unix_toi"]):
        print(dict(element.items()))

    print(".. Values .....")
    message_trace = Trace(w)
    message_importer = DBMessageImporter()
    message_importer.import_messages(message_trace, db)
    for k, v in message_trace.values.items():
        print("\t", k, list(i for i in v.items()))

    print(".. Predicates .....")
    for k, v in message_trace.mtl_predicates.items():
        print("\t", k, list(i for i in v.items()))

    print(".. Hazards .....")
    for h in hazards:
        print("{} -".format(h.name), h.description)
        print("\t", message_trace.evaluate(h.condition))

    print(".. Missing .....")
    for p in sorted(message_trace.undefined_terms):
        print("\t", ".".join(p))

    print(".. Aliases .....")
    for alias, alias_terms in sorted(message_trace.aliased_terms.items()):
        print("\t", ".".join(alias), sorted(map(lambda i: ".".join(i), alias_terms)))
