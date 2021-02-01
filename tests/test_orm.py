from csi.twin.orm import DataBase


class TestOrm:
    def test_output(self):
        db = DataBase("./fixtures/csi.db")
        for element in sorted(db.messages(), key=lambda m: m["unix_toi"]):
            e = {k: v for k, v in element.items()}
            print("\t", e)
        assert True
