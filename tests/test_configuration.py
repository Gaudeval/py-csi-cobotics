import json

from csi.configuration import ConfigurationManager
from scenarios.tcx.configuration import Operator, WorldData


class TestConfiguration:
    def test_output(self):
        world = WorldData()
        world.operator = Operator()
        print(ConfigurationManager(WorldData).encode(world))

        w = ConfigurationManager(WorldData).load("./fixtures/csi.json")
        print(w)

        ConfigurationManager(WorldData).save(w, "./fixtures/csi-test.json")
        assert json.load(open("./fixtures/csi.json")) == json.load(
            open("./fixtures/csi-test.json")
        )
