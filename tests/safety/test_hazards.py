from tests.safety.common import SafetyTest
from csi.monitor import Trace, Monitor
from experiments.tcx_safety.wrapper.safety import hazards, P


class HazardTest(SafetyTest):
    hazard_id = None

    @property
    def hazard(self):
        return self.identify(self.hazard_id)

    @staticmethod
    def identify(hazard_id):
        for hazard in hazards:
            if hazard.uid == hazard_id:
                return hazard

    def evaluate(self, trace, expected=True):
        hazard = self.hazard
        monitor = Monitor({hazard.condition})
        assert len(monitor.atoms() - trace.atoms()) == 0, (
            monitor.atoms() - trace.atoms()
        )
        occurs = monitor.evaluate(trace, hazard.condition)
        assert occurs is not None
        assert occurs == expected


class TestH1(HazardTest):
    hazard_id = 1
    hazard_desc = "Violation of minimum separation requirements"

    def setup_trace(self):
        trace = Trace()
        trace[P.constraints.cobot.distance.proximity] = (0, 100)
        trace[P.constraints.cobot.velocity.oob] = (0, 100)
        trace[P.constraints.cobot.velocity.in_bench] = (0, 100)
        trace[P.constraints.cobot.velocity.in_tool] = (0, 100)
        trace[P.constraints.cobot.velocity.in_workspace] = (0, 100)
        trace[P.constraints.cobot.velocity.proximity] = (0, 100)
        trace[P.cobot.distance] = (0, 0)
        trace[P.cobot.has_assembly] = (0, False)
        trace[P.cobot.has_assembly] = (0, False)
        trace[P.cobot.position.in_tool] = (0, False)
        trace[P.cobot.position.in_bench] = (0, False)
        trace[P.cobot.position.in_workspace] = (0, False)
        trace[P.cobot.velocity] = (0, 0)
        trace[P.operator.has_assembly] = (0, False)
        trace[P.assembly.has_assembly] = (0, False)
        trace[P.tool.has_assembly] = (0, False)
        return trace

    def test_nominal(self):
        trace = self.setup_trace()
        self.evaluate(trace, expected=False)

    def test_occurs_manipulators(self):
        # Two manipulators hold on the assembly
        trace = self.setup_trace()
        #
        trace[P.operator.has_assembly] = (0, True)
        trace[P.cobot.has_assembly] = (0, True)
        #
        self.evaluate(trace)

    def test_nominal_manipulators(self):
        # Two manipulators hold on the assembly
        trace = self.setup_trace()
        #
        trace[P.cobot.has_assembly] = (0, False)
        trace[P.operator.has_assembly] = (0, True)
        trace[P.operator.has_assembly] = (1, False)
        trace[P.cobot.has_assembly] = (2, True)
        trace[P.cobot.has_assembly] = (3, False)
        trace[P.operator.has_assembly] = (4, True)
        #
        self.evaluate(trace, expected=False)

    def test_nominal_velocity(self):
        # Cobot moving faster than authorised at specific locations
        trace = self.setup_trace()
        trace[P.constraints.cobot.velocity.in_tool] = (0, 10)
        trace[P.constraints.cobot.velocity.in_workspace] = (0, 10)
        trace[P.constraints.cobot.velocity.in_bench] = (0, 10)
        trace[P.cobot.velocity] = (0, 1)
        trace[P.cobot.position.in_bench] = (0, True)
        trace[P.cobot.position.in_bench] = (1, False)
        trace[P.cobot.position.in_tool] = (1, True)
        trace[P.cobot.position.in_tool] = (2, False)
        trace[P.cobot.position.in_workspace] = (2, True)
        self.evaluate(trace, expected=False)

    def test_occurs_passing_velocity(self):
        # Cobot moving faster than authorised at specific locations
        trace = self.setup_trace()
        trace[P.constraints.cobot.velocity.in_tool] = (0, 10)
        trace[P.constraints.cobot.velocity.in_workspace] = (0, 0)
        trace[P.constraints.cobot.velocity.in_bench] = (0, 10)
        trace[P.cobot.velocity] = (0, 1)
        trace[P.cobot.position.in_bench] = (0, True)
        trace[P.cobot.position.in_bench] = (1, False)
        trace[P.cobot.position.in_tool] = (1, True)
        trace[P.cobot.position.in_tool] = (2, False)
        trace[P.cobot.position.in_workspace] = (2, True)
        self.evaluate(trace)

    def test_occurs_velocity_bench(self):
        # Cobot moving faster than authorised at specific locations
        trace = self.setup_trace()
        trace[P.constraints.cobot.velocity.in_tool] = (0, 10)
        trace[P.constraints.cobot.velocity.in_workspace] = (0, 10)
        trace[P.constraints.cobot.velocity.in_bench] = (0, 0)
        trace[P.cobot.position.in_bench] = (0, True)
        trace[P.cobot.velocity] = (0, 1)
        self.evaluate(trace)

    def test_occurs_velocity_tool(self):
        # Cobot moving faster than authorised at specific locations
        trace = self.setup_trace()
        trace[P.constraints.cobot.velocity.in_tool] = (0, 0)
        trace[P.constraints.cobot.velocity.in_workspace] = (0, 10)
        trace[P.constraints.cobot.velocity.in_bench] = (0, 10)
        trace[P.cobot.position.in_tool] = (0, True)
        trace[P.cobot.velocity] = (0, 1)
        self.evaluate(trace)

    def test_occurs_velocity_workspace(self):
        # Cobot moving faster than authorised at specific locations
        trace = self.setup_trace()
        trace[P.constraints.cobot.velocity.in_tool] = (0, 10)
        trace[P.constraints.cobot.velocity.in_workspace] = (0, 0)
        trace[P.constraints.cobot.velocity.in_bench] = (0, 10)
        trace[P.cobot.position.in_workspace] = (0, True)
        trace[P.cobot.velocity] = (0, 1)
        self.evaluate(trace)

    def test_occurs_velocity_proximity(self):
        # Cobot moving faster than authorised in close proximity
        trace = self.setup_trace()
        trace[P.constraints.cobot.distance.proximity] = (0, 10)
        trace[P.constraints.cobot.velocity.proximity] = (0, 0)
        trace[P.cobot.distance] = (0, 0)
        trace[P.cobot.velocity] = (0, 1)
        self.evaluate(trace)

    def test_nominal_velocity_proximity(self):
        # Cobot moving faster than authorised in close proximity
        trace = self.setup_trace()
        trace[P.constraints.cobot.distance.proximity] = (0, 10)
        trace[P.constraints.cobot.velocity.proximity] = (0, 10)
        trace[P.cobot.distance] = (0, 0)
        trace[P.cobot.velocity] = (0, 5)
        self.evaluate(trace, expected=False)

    def test_nominal_velocity_no_proximity(self):
        # Cobot moving faster than authorised in close proximity
        trace = self.setup_trace()
        trace[P.constraints.cobot.distance.proximity] = (0, 10)
        trace[P.constraints.cobot.velocity.proximity] = (0, 0)
        trace[P.cobot.distance] = (0, 20)
        trace[P.cobot.velocity] = (0, 5)
        self.evaluate(trace, expected=False)

    def test_occurs_proximity_change(self):
        # Cobot moving faster than authorised in close proximity
        trace = self.setup_trace()
        trace[P.constraints.cobot.distance.proximity] = (0, 10)
        trace[P.constraints.cobot.velocity.proximity] = (0, 0)
        trace[P.cobot.distance] = (0, 20)
        trace[P.cobot.velocity] = (0, 5)
        trace[P.cobot.distance] = (1, 0)
        self.evaluate(trace)

    def test_nominal_proximity_change(self):
        # Cobot moving faster than authorised in close proximity
        trace = self.setup_trace()
        trace[P.constraints.cobot.distance.proximity] = (0, 10)
        trace[P.constraints.cobot.velocity.proximity] = (0, 5)
        #
        trace[P.cobot.distance] = (0, 20)
        trace[P.cobot.velocity] = (0, 10)
        #
        trace[P.cobot.distance] = (1, 5)
        trace[P.cobot.velocity] = (1, 1)
        #
        trace[P.cobot.distance] = (2, 20)
        trace[P.cobot.velocity] = (2, 30)
        self.evaluate(trace, expected=False)


class TestH2(HazardTest):
    hazard_id = 2
    hazard_desc = "Individual or Object in dangerous area"

    def setup_trace(self):
        trace = Trace()
        trace[P.constraints.tool.distance.operation] = (0, 10)
        trace[P.tool.distance] = (0, 0)
        trace[P.tool.is_running] = (0, False)
        return trace

    def test_occurs(self):
        trace = self.setup_trace()
        trace[P.constraints.tool.distance.operation] = (0, 10)
        trace[P.tool.distance] = (0, 0)
        trace[P.tool.is_running] = (0, True)
        self.evaluate(trace)

    def test_nominal_safety_distance(self):
        trace = self.setup_trace()
        trace[P.constraints.tool.distance.operation] = (0, 10)
        trace[P.tool.distance] = (0, 20)
        trace[P.tool.is_running] = (0, True)
        self.evaluate(trace, expected=False)

    def test_nominal_stopped(self):
        trace = self.setup_trace()
        trace[P.constraints.tool.distance.operation] = (0, 10)
        trace[P.tool.distance] = (0, 0)
        trace[P.tool.is_running] = (0, False)
        self.evaluate(trace, expected=False)

    def test_nominal_proximity_stop(self):
        trace = self.setup_trace()
        trace[P.constraints.tool.distance.operation] = (0, 10)
        trace[P.tool.distance] = (0, 20)
        trace[P.tool.is_running] = (0, True)
        trace[P.tool.distance] = (1, 0)
        trace[P.tool.is_running] = (1, False)
        trace[P.tool.distance] = (2, 20)
        trace[P.tool.is_running] = (2, True)
        self.evaluate(trace, expected=False)

    def test_nominal_start(self):
        trace = self.setup_trace()
        trace[P.constraints.tool.distance.operation] = (0, 10)
        trace[P.tool.distance] = (0, 0)
        trace[P.tool.is_running] = (0, False)
        trace[P.tool.is_running] = (1, True)
        self.evaluate(trace)


class TestH3(HazardTest):
    hazard_id = 3
    hazard_desc = "Equipment or Component subject to unnecessary stress"

    def setup_trace(self):
        trace = Trace()
        trace[P.assembly.is_damaged] = (0, False)
        trace[P.cobot.is_damaged] = (0, False)
        trace[P.operator.is_damaged] = (0, False)
        trace[P.tool.is_damaged] = (0, False)
        return trace

    def test_occurs_assembly(self):
        trace = self.setup_trace()
        trace[P.assembly.is_damaged] = (1, True)
        self.evaluate(trace)

    def test_occurs_cobot(self):
        trace = self.setup_trace()
        trace[P.cobot.is_damaged] = (1, True)
        self.evaluate(trace)

    def test_occurs_operator(self):
        trace = self.setup_trace()
        trace[P.operator.is_damaged] = (1, True)
        self.evaluate(trace)

    def test_occurs_tool(self):
        trace = self.setup_trace()
        trace[P.tool.is_damaged] = (1, True)
        self.evaluate(trace)

    def test_nominal(self):
        trace = self.setup_trace()
        self.evaluate(trace, expected=False)

    def test_nominal_initial(self):
        # FIXME No tolerance currently for damaged assembly on start
        trace = self.setup_trace()
        trace[P.assembly.is_damaged] = (0, True)
        self.evaluate(trace, expected=False)


class TestH4(HazardTest):
    hazard_id = 4
    hazard_desc = "Supplied component cannot be correctly processed"

    def setup_trace(self):
        trace = Trace()
        trace[P.assembly.is_damaged] = (0, False)
        trace[P.assembly.is_orientation_valid] = (0, True)
        trace[P.assembly.is_valid] = (0, True)
        trace[P.assembly.under_processing] = (0, False)
        return trace

    def test_occurs_damaged(self):
        trace = self.setup_trace()
        trace[P.assembly.is_damaged] = (0, True)
        trace[P.assembly.under_processing] = (0, True)
        self.evaluate(trace)

    def test_occurs_orientation(self):
        trace = self.setup_trace()
        trace[P.assembly.is_orientation_valid] = (0, False)
        trace[P.assembly.under_processing] = (0, True)
        self.evaluate(trace)

    def test_occurs_valid(self):
        trace = self.setup_trace()
        trace[P.assembly.is_valid] = (0, False)
        trace[P.assembly.under_processing] = (0, True)
        self.evaluate(trace)

    def test_nominal(self):
        trace = self.setup_trace()
        trace[P.assembly.is_damaged] = (0, False)
        trace[P.assembly.is_orientation_valid] = (0, True)
        trace[P.assembly.is_valid] = (0, True)
        trace[P.assembly.under_processing] = (0, True)
        self.evaluate(trace, expected=False)

    def test_nominal_no_processing(self):
        trace = self.setup_trace()
        trace[P.assembly.is_damaged] = (0, False)
        trace[P.assembly.is_orientation_valid] = (0, True)
        trace[P.assembly.is_valid] = (0, True)
        trace[P.assembly.under_processing] = (0, False)
        self.evaluate(trace, expected=False)

    def test_nominal_damaged_after(self):
        trace = self.setup_trace()
        trace[P.assembly.is_damaged] = (0, False)
        trace[P.assembly.under_processing] = (0, True)
        trace[P.assembly.under_processing] = (1, False)
        trace[P.assembly.is_damaged] = (2, True)
        self.evaluate(trace, expected=False)


class TestH5(HazardTest):
    hazard_id = 5
    hazard_desc = "Equipment operated outside safe conditions [Temp: Tool running without assembly]"

    def setup_trace(self):
        trace = Trace()
        return trace

    def test_occurs(self):
        trace = self.setup_trace()
        trace[P.cobot.has_assembly] = (0, False)
        trace[P.cobot.position.in_tool] = (0, True)
        trace[P.tool.is_running] = (0, True)
        self.evaluate(trace)

    def test_occurs_drop(self):
        trace = self.setup_trace()
        trace[P.cobot.has_assembly] = (0, True)
        trace[P.cobot.position.in_tool] = (0, True)
        trace[P.tool.is_running] = (0, True)
        trace[P.cobot.has_assembly] = (1, False)
        self.evaluate(trace)

    def test_nominal(self):
        trace = self.setup_trace()
        trace[P.cobot.has_assembly] = (0, True)
        trace[P.cobot.position.in_tool] = (0, True)
        trace[P.tool.is_running] = (0, True)
        self.evaluate(trace, expected=False)

    def test_nominal_with_release(self):
        trace = self.setup_trace()
        trace[P.cobot.has_assembly] = (0, True)
        trace[P.cobot.position.in_tool] = (0, True)
        trace[P.tool.is_running] = (0, True)
        trace[P.tool.is_running] = (2, False)
        trace[P.cobot.has_assembly] = (3, False)
        self.evaluate(trace, expected=False)

    def test_occurs_wrong_position(self):
        trace = self.setup_trace()
        trace[P.cobot.has_assembly] = (0, True)
        trace[P.cobot.position.in_tool] = (0, False)
        trace[P.tool.is_running] = (0, True)
        self.evaluate(trace)


class TestH6(HazardTest):
    hazard_id = 6
    hazard_desc = "Components not secured during processing or transport"

    def setup_trace(self):
        trace = Trace()
        trace[P.assembly.is_moving] = (0, False)
        trace[P.assembly.is_secured] = (0, True)
        trace[P.assembly.under_processing] = (0, False)
        return trace

    def test_occurs_moving(self):
        trace = self.setup_trace()
        trace[P.assembly.is_moving] = (0, True)
        trace[P.assembly.is_secured] = (0, False)
        trace[P.assembly.under_processing] = (0, False)
        self.evaluate(trace)

    def test_occurs_processing(self):
        trace = self.setup_trace()
        trace[P.assembly.is_moving] = (0, False)
        trace[P.assembly.is_secured] = (0, False)
        trace[P.assembly.under_processing] = (0, True)
        self.evaluate(trace)

    def test_nominal_moving(self):
        trace = self.setup_trace()
        trace[P.assembly.is_moving] = (0, True)
        trace[P.assembly.is_secured] = (0, True)
        trace[P.assembly.under_processing] = (0, False)
        self.evaluate(trace, expected=False)

    def test_nominal_processing(self):
        trace = self.setup_trace()
        trace[P.assembly.is_moving] = (0, False)
        trace[P.assembly.is_secured] = (0, True)
        trace[P.assembly.under_processing] = (0, True)
        self.evaluate(trace, expected=False)


class TestH7(HazardTest):
    hazard_id = 7
    hazard_desc = "Components do not move through the processing chain"

    def setup_trace(self):
        trace = Trace()
        trace[P.assembly.position.in_bench] = (0, True)
        trace[P.assembly.is_processed] = (0, False)
        trace[P.cobot.has_assembly] = (0, True)
        trace[P.operator.has_assembly] = (0, False)
        trace[P.tool.has_assembly] = (0, False)
        trace[P.assembly.has_assembly] = (0, False)
        return trace

    def test_occurs(self):
        trace = self.setup_trace()
        self.evaluate(trace)

    def test_nominal(self):
        trace = self.setup_trace()
        trace[P.assembly.position.in_bench] = (0, True)
        trace[P.cobot.has_assembly] = (0, False)
        #
        trace[P.operator.has_assembly] = (0, True)
        trace[P.operator.has_assembly] = (1, False)
        #
        trace[P.cobot.has_assembly] = (2, True)
        #
        trace[P.assembly.is_processed] = (3, True)
        #
        trace[P.cobot.has_assembly] = (4, False)
        self.evaluate(trace, expected=False)
