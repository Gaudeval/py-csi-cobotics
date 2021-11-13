import pytest

from tests.safety.common import SafetyTest
from csi.monitor import Monitor, Trace
from experiments.tcx_safety.wrapper.safety import P


class UCATest(SafetyTest):
    uca_id = None

    @property
    def uca(self):
        return self.identify(self.uca_id)

    @staticmethod
    def identify(uca_id):
        from experiments.tcx_safety.wrapper.safety import unsafe_control_actions

        for uca in unsafe_control_actions:
            if uca.uid == uca_id:
                return uca

    def evaluate(self, trace, expected=True):
        uca = self.identify(self.uca_id)
        monitor = Monitor({uca.condition})
        assert len(monitor.atoms() - trace.atoms()) == 0
        occurs = monitor.evaluate(trace, uca.condition)
        assert occurs is not None
        assert occurs == expected


class Test4D1(UCATest):
    uca_id = "UCA4-D-1"
    uca_desc = (
        "The Operator keeps holding on to a secured Component while the Cobot is moving to another position.",
    )

    def test_grab(self):
        trace = Trace()
        #
        trace[P.operator.has_assembly] = (0, False)
        trace[P.cobot.has_assembly] = (0, False)
        trace[P.cobot.is_moving] = (0, False)
        #
        trace[P.cobot.is_moving] = (1, True)
        trace[P.cobot.is_moving] = (2, False)
        trace[P.operator.has_assembly] = (2, True)
        trace[P.cobot.has_assembly] = (3, True)
        trace[P.cobot.is_moving] = (4, True)
        self.evaluate(trace)

    def test_operator_release(self):
        trace = Trace()
        #
        trace[P.operator.has_assembly] = (0, True)
        trace[P.cobot.has_assembly] = (0, False)
        trace[P.cobot.is_moving] = (0, False)
        #
        trace[P.cobot.is_moving] = (1, True)
        trace[P.cobot.is_moving] = (2, False)
        trace[P.operator.has_assembly] = (2, False)
        trace[P.cobot.has_assembly] = (3, True)
        trace[P.cobot.is_moving] = (4, True)
        self.evaluate(trace, expected=False)

    def test_cobot_release(self):
        trace = Trace()
        #
        trace[P.operator.has_assembly] = (0, False)
        trace[P.cobot.has_assembly] = (0, False)
        trace[P.cobot.is_moving] = (0, True)
        trace[P.cobot.is_moving] = (1, False)
        #
        trace[P.cobot.has_assembly] = (1, True)
        trace[P.operator.has_assembly] = (2, True)
        trace[P.cobot.has_assembly] = (3, False)
        trace[P.cobot.is_moving] = (4, True)
        self.evaluate(trace, expected=False)


class Test4D2(UCATest):
    uca_id = "UCA4-D-2"
    uca_desc = "The Operator releases a Component before it is secured"

    def test_occurs(self):
        trace = Trace()
        trace[P.assembly.is_secured] = (0, False)
        trace[P.operator.has_assembly] = (0, True)
        trace[P.operator.has_assembly] = (1, False)
        self.evaluate(trace)

    def test_nominal(self):
        trace = Trace()
        trace[P.assembly.is_secured] = (0, True)
        trace[P.operator.has_assembly] = (0, True)
        trace[P.operator.has_assembly] = (1, False)
        self.evaluate(trace, expected=False)

    def test_multiple_occurs(self):
        trace = Trace()
        trace[P.assembly.is_secured] = (0, True)
        trace[P.operator.has_assembly] = (0, True)
        trace[P.operator.has_assembly] = (1, False)
        trace[P.assembly.is_secured] = (2, False)
        trace[P.operator.has_assembly] = (3, True)
        trace[P.operator.has_assembly] = (4, False)
        self.evaluate(trace)

    def test_no_release(self):
        trace = Trace()
        trace[P.assembly.is_secured] = (0, False)
        trace[P.operator.has_assembly] = (0, True)
        self.evaluate(trace, expected=False)

    def test_unsecured_after(self):
        trace = Trace()
        trace[P.assembly.is_secured] = (0, True)
        trace[P.operator.has_assembly] = (0, True)
        trace[P.operator.has_assembly] = (1, False)
        trace[P.assembly.is_secured] = (1, False)
        self.evaluate(trace, expected=False)

    def test_becomes_unsecured(self):
        trace = Trace()
        trace[P.assembly.is_secured] = (0, True)
        trace[P.assembly.is_secured] = (5, False)
        trace[P.operator.has_assembly] = (10, True)
        trace[P.operator.has_assembly] = (11, False)
        self.evaluate(trace)


class Test4N1(UCATest):
    uca_id = "UCA4-N-1"
    uca_desc = "The Operator does not provide a Component when one is available and the Cobot is ready"

    def setup_trace(self):
        trace = Trace()
        trace[P.operator.provides_assembly] = (0, False)
        trace[P.cobot.has_assembly] = (0, False)
        trace[P.cobot.position.in_tool] = (0, True)
        trace[P.operator.has_assembly] = (0, False)
        return trace

    def test_occurs(self):
        trace = self.setup_trace()
        trace[P.operator.provides_assembly] = (0, False)
        trace[P.operator.has_assembly] = (0, True)
        trace[P.cobot.has_assembly] = (0, False)
        trace[P.cobot.position.in_bench] = (0, True)
        self.evaluate(trace)

    def test_nominal(self):
        trace = self.setup_trace()
        trace[P.operator.has_assembly] = (0, True)
        trace[P.operator.provides_assembly] = (0, True)
        trace[P.cobot.has_assembly] = (0, False)
        trace[P.cobot.position.in_bench] = (0, True)
        trace[P.operator.has_assembly] = (1, False)
        self.evaluate(trace, expected=False)

    def test_cobot_busy(self):
        trace = self.setup_trace()
        trace[P.operator.provides_assembly] = (0, False)
        trace[P.operator.has_assembly] = (0, True)
        trace[P.cobot.has_assembly] = (0, True)
        trace[P.cobot.position.in_bench] = (0, True)
        self.evaluate(trace, expected=False)

    def test_no_assembly(self):
        trace = Trace()
        trace[P.operator.provides_assembly] = (0, False)
        trace[P.operator.has_assembly] = (0, False)
        trace[P.cobot.has_assembly] = (0, True)
        trace[P.cobot.position.in_bench] = (0, True)
        self.evaluate(trace, expected=False)

    def test_nominal_multiple(self):
        trace = self.setup_trace()
        # Cobot in position
        trace[P.cobot.has_assembly] = (0, False)
        trace[P.cobot.position.in_bench] = (0, True)
        # Operator ready for handover
        trace[P.operator.has_assembly] = (0, True)
        trace[P.operator.provides_assembly] = (0, True)
        # Handover
        trace[P.operator.has_assembly] = (1, False)
        trace[P.operator.provides_assembly] = (1, False)
        # Cobot releases assembly
        trace[P.cobot.has_assembly] = (1, True)
        trace[P.cobot.has_assembly] = (2, False)
        # Operator picks assembly
        trace[P.operator.has_assembly] = (3, True)
        trace[P.operator.provides_assembly] = (4, True)
        # Handover
        trace[P.operator.has_assembly] = (5, False)
        trace[P.operator.provides_assembly] = (5, False)
        self.evaluate(trace, expected=False)

    def test_occurs_after_nominal(self):
        trace = self.setup_trace()
        # Nominal handover
        trace[P.operator.has_assembly] = (0, True)
        trace[P.operator.provides_assembly] = (0, True)
        trace[P.cobot.has_assembly] = (0, False)
        trace[P.cobot.position.in_bench] = (0, True)
        trace[P.operator.has_assembly] = (1, False)
        # Cobot release, no handover
        trace[P.operator.provides_assembly] = (2, False)
        trace[P.cobot.has_assembly] = (2, True)
        trace[P.cobot.has_assembly] = (3, False)
        trace[P.operator.has_assembly] = (3, True)
        self.evaluate(trace)

    def test_occurs_before_nominal(self):
        trace = self.setup_trace()
        trace[P.operator.provides_assembly] = (0, False)
        trace[P.operator.has_assembly] = (0, True)
        trace[P.cobot.has_assembly] = (0, False)
        trace[P.cobot.position.in_bench] = (0, True)
        # Nominal handover
        trace[P.operator.has_assembly] = (5, True)
        trace[P.operator.provides_assembly] = (5, True)
        trace[P.cobot.has_assembly] = (5, False)
        trace[P.cobot.position.in_bench] = (5, True)
        trace[P.operator.has_assembly] = (6, False)
        self.evaluate(trace, expected=False)


class Test4P1(UCATest):
    uca_id = "UCA4-P-1"
    uca_desc = "The Operator provides a Component when the controller has been configured for a different Component"

    def setup_trace(self):
        trace = Trace()
        trace[P.assembly.is_valid] = (0, False)
        trace[P.operator.provides_assembly] = (0, False)
        return trace

    def test_occurs(self):
        trace = self.setup_trace()
        trace[P.assembly.is_valid] = (0, False)
        trace[P.operator.provides_assembly] = (0, True)
        self.evaluate(trace)

    def test_assembly_valid(self):
        trace = self.setup_trace()
        trace[P.assembly.is_valid] = (0, True)
        trace[P.operator.provides_assembly] = (0, True)
        self.evaluate(trace, expected=False)

    def test_no_provision(self):
        trace = self.setup_trace()
        trace[P.assembly.is_valid] = (0, True)
        trace[P.operator.provides_assembly] = (0, False)
        self.evaluate(trace, expected=False)


class Test4P2(UCATest):
    uca_id = "UCA4-P-2"
    uca_desc = "The Operator provides an unprepared or damaged Component"

    def setup_trace(self):
        trace = Trace()
        trace[P.assembly.is_damaged] = (0, False)
        trace[P.operator.provides_assembly] = (0, False)
        return trace

    def test_occurs(self):
        trace = self.setup_trace()
        trace[P.assembly.is_damaged] = (0, True)
        trace[P.operator.provides_assembly] = (0, True)
        self.evaluate(trace)

    def test_assembly_valid(self):
        trace = self.setup_trace()
        trace[P.assembly.is_damaged] = (0, False)
        trace[P.operator.provides_assembly] = (0, True)
        self.evaluate(trace, expected=False)

    def test_no_provision(self):
        trace = self.setup_trace()
        trace[P.assembly.is_damaged] = (0, True)
        trace[P.operator.provides_assembly] = (0, False)
        self.evaluate(trace, expected=False)


class Test4P3(UCATest):
    uca_id = "UCA4-P-3"
    uca_desc = "The Operator provides a Component in the wrong position or orientation"

    def setup_trace(self):
        trace = Trace()
        trace[P.assembly.is_orientation_valid] = (0, False)
        trace[P.operator.provides_assembly] = (0, False)
        return trace

    def test_occurs(self):
        trace = self.setup_trace()
        trace[P.assembly.is_orientation_valid] = (0, False)
        trace[P.operator.provides_assembly] = (0, True)
        self.evaluate(trace)

    def test_assembly_valid(self):
        trace = self.setup_trace()
        trace[P.assembly.is_orientation_valid] = (0, True)
        trace[P.operator.provides_assembly] = (0, True)
        self.evaluate(trace, expected=False)

    def test_no_provision(self):
        trace = self.setup_trace()
        trace[P.assembly.is_orientation_valid] = (0, False)
        trace[P.operator.provides_assembly] = (0, False)
        self.evaluate(trace, expected=False)


class Test4T1(UCATest):
    uca_id = "UCA4-T-1"
    uca_desc = "The Operator provides a Component to the Cobot while another is being processed"

    def test_occurs(self):
        trace = Trace()
        #
        trace[P.assembly.under_processing] = (0, True)
        trace[P.operator.provides_assembly] = (0, True)
        self.evaluate(trace)

    def test_no_provision(self):
        trace = Trace()
        #
        trace[P.assembly.under_processing] = (0, True)
        trace[P.operator.provides_assembly] = (0, False)
        self.evaluate(trace, expected=False)


class Test4T2(UCATest):
    uca_id = "UCA4-T-2"
    uca_desc = "The Operator provides a Component to the Cobot while it is approaching for the handover"

    def setup_trace(self):
        trace = Trace()
        trace[P.cobot.is_moving] = (0, False)
        # trace[P.cobot.position] = (0, EntityPosition.OOB)
        trace[P.operator.provides_assembly] = (0, False)
        return trace

    def test_occurs(self):
        trace = self.setup_trace()
        trace[P.cobot.is_moving] = (0, True)
        trace[P.cobot.position.in_bench] = (0, True)
        trace[P.operator.provides_assembly] = (1, True)
        self.evaluate(trace)

    def test_no_delivery(self):
        trace = self.setup_trace()
        #
        trace[P.cobot.is_moving] = (0, True)
        trace[P.cobot.position.in_tool] = (0, True)
        trace[P.cobot.position.in_tool] = (1, False)
        trace[P.cobot.position.in_bench] = (1, True)
        trace[P.cobot.position.in_bench] = (2, False)
        trace[P.cobot.position.in_tool] = (2, True)
        trace[P.operator.provides_assembly] = (0, False)
        self.evaluate(trace, expected=False)

    def test_cobot_leaving(self):
        trace = self.setup_trace()
        trace[P.cobot.is_moving] = (0, True)
        trace[P.cobot.position.in_tool] = (0, True)
        trace[P.cobot.position.in_tool] = (1, False)
        trace[P.cobot.position.in_bench] = (1, True)
        trace[P.cobot.position.in_bench] = (2, False)
        trace[P.cobot.position.in_tool] = (2, True)
        trace[P.operator.provides_assembly] = (2, True)
        self.evaluate(trace, expected=False)


class Test4T3(UCATest):
    uca_id = "UCA4-T-3"
    uca_desc = (
        "The Operator provides a Component when the controller has not been configured"
    )

    def setup_trace(self):
        trace = Trace()
        trace[P.operator.provides_assembly] = (0, False)
        trace[P.controller.is_configured] = (0, False)
        return trace

    def test_occurs(self):
        trace = self.setup_trace()
        trace[P.controller.is_configured] = (0, False)
        trace[P.operator.provides_assembly] = (0, True)
        self.evaluate(trace)

    def test_configured(self):
        trace = self.setup_trace()
        trace[P.controller.is_configured] = (0, True)
        trace[P.operator.provides_assembly] = (0, True)
        self.evaluate(trace, expected=False)

    def test_delayed_configuration(self):
        trace = self.setup_trace()
        #
        trace[P.controller.is_configured] = (0, False)
        trace[P.controller.is_configured] = (5, True)
        trace[P.operator.provides_assembly] = (6, True)
        self.evaluate(trace, expected=False)

    def test_configuration_removed(self):
        trace = self.setup_trace()
        #
        trace[P.controller.is_configured] = (0, False)
        trace[P.controller.is_configured] = (1, True)
        trace[P.operator.provides_assembly] = (2, True)
        trace[P.operator.provides_assembly] = (3, False)
        trace[P.controller.is_configured] = (5, False)
        self.evaluate(trace, expected=False)


class Test5D1(UCATest):
    uca_id = "UCA5-D-1"
    uca_desc = "The Operator releases a Component before he has secured it"

    def test_occurs(self):
        trace = Trace()
        #
        trace[P.assembly.is_secured] = (0, False)
        trace[P.operator.has_assembly] = (0, True)
        trace[P.operator.has_assembly] = (1, False)
        self.evaluate(trace)

    def test_secured(self):
        trace = Trace()
        #
        trace[P.assembly.is_secured] = (0, True)
        trace[P.operator.has_assembly] = (0, True)
        trace[P.operator.has_assembly] = (1, False)
        self.evaluate(trace, expected=False)

    def test_secured_release(self):
        trace = Trace()
        #
        trace[P.assembly.is_secured] = (0, False)
        trace[P.operator.has_assembly] = (0, True)
        trace[P.assembly.is_secured] = (1, True)
        trace[P.operator.has_assembly] = (2, False)
        self.evaluate(trace, expected=False)

    def test_occurs_once(self):
        trace = Trace()
        #
        trace[P.assembly.is_secured] = (0, True)
        trace[P.operator.has_assembly] = (0, True)
        trace[P.operator.has_assembly] = (1, False)
        trace[P.assembly.is_secured] = (10, False)
        trace[P.operator.has_assembly] = (10, True)
        trace[P.operator.has_assembly] = (11, False)
        self.evaluate(trace)


class Test5P1(UCATest):
    uca_id = "UCA5-P-1"
    uca_desc = "The Operator retrieves the Component while it is secured by the Cobot"

    def test_occurs(self):
        trace = Trace()
        trace[P.assembly.is_secured] = (0, True)
        trace[P.cobot.has_assembly] = (0, True)
        trace[P.operator.has_assembly] = (0, False)
        trace[P.operator.has_assembly] = (1, True)
        self.evaluate(trace)

    def test_nominal(self):
        trace = Trace()
        trace[P.assembly.is_secured] = (0, True)
        trace[P.cobot.has_assembly] = (0, False)
        trace[P.operator.has_assembly] = (0, False)
        trace[P.operator.has_assembly] = (1, True)
        self.evaluate(trace, expected=False)

    def test_unsecured(self):
        trace = Trace()
        trace[P.assembly.is_secured] = (0, False)
        trace[P.cobot.has_assembly] = (0, True)
        trace[P.operator.has_assembly] = (0, False)
        trace[P.operator.has_assembly] = (1, True)
        self.evaluate(trace, expected=False)

    def test_no_retrieve(self):
        trace = Trace()
        trace[P.assembly.is_secured] = (0, True)
        trace[P.cobot.has_assembly] = (0, True)
        trace[P.operator.has_assembly] = (0, False)
        self.evaluate(trace, expected=False)

    def test_cobot_release(self):
        trace = Trace()
        trace[P.assembly.is_secured] = (0, True)
        trace[P.cobot.has_assembly] = (0, True)
        trace[P.cobot.has_assembly] = (1, False)
        trace[P.operator.has_assembly] = (0, False)
        trace[P.operator.has_assembly] = (2, False)
        self.evaluate(trace, expected=False)


class Test5P2(UCATest):
    uca_id = "UCA5-P-2"
    uca_test = "The Operator retrieves the Component while it is being processed."

    def setup_trace(self):
        trace = Trace()
        trace[P.operator.has_assembly] = (0, True)
        trace[P.assembly.under_processing] = (0, False)
        return trace

    def test_occurs(self):
        trace = self.setup_trace()
        trace[P.assembly.under_processing] = (0, True)
        trace[P.operator.has_assembly] = (0, False)
        trace[P.operator.has_assembly] = (1, True)
        self.evaluate(trace)

    def test_nominal(self):
        trace = self.setup_trace()
        trace[P.assembly.under_processing] = (0, False)
        trace[P.operator.has_assembly] = (0, False)
        trace[P.operator.has_assembly] = (1, True)
        self.evaluate(trace, expected=False)

    def test_after_processing(self):
        trace = self.setup_trace()
        trace[P.assembly.under_processing] = (0, True)
        trace[P.assembly.under_processing] = (1, False)
        trace[P.operator.has_assembly] = (1, False)
        trace[P.operator.has_assembly] = (2, True)
        self.evaluate(trace, expected=False)


class Test5P3(UCATest):
    uca_id = "UCA5-P-3"
    uca_desc = "The Operator retrieves a Component before it has been processed"

    def setup_trace(self):
        trace = Trace()
        trace[P.operator.has_assembly] = (0, False)
        trace[P.assembly.is_processed] = (0, False)
        return trace

    def test_occurs(self):
        trace = self.setup_trace()
        trace[P.operator.has_assembly] = (0, False)
        trace[P.assembly.is_processed] = (0, False)
        trace[P.operator.has_assembly] = (1, True)
        self.evaluate(trace)

    def test_nominal(self):
        trace = self.setup_trace()
        trace[P.operator.has_assembly] = (0, False)
        trace[P.assembly.is_processed] = (0, True)
        trace[P.operator.has_assembly] = (1, True)
        self.evaluate(trace, expected=False)

    def test_multiple_occurs(self):
        trace = self.setup_trace()
        # Grab processed
        trace[P.operator.has_assembly] = (0, False)
        trace[P.assembly.is_processed] = (0, True)
        trace[P.operator.has_assembly] = (1, True)
        # Grab non-processed
        trace[P.operator.has_assembly] = (2, False)
        trace[P.assembly.is_processed] = (True, False)
        trace[P.operator.has_assembly] = (4, True)
        self.evaluate(trace)

    def test_processed_no_grab(self):
        trace = self.setup_trace()
        # Grab non-processed
        trace[P.operator.has_assembly] = (0, False)
        trace[P.cobot.has_assembly] = (0, True)
        trace[P.cobot.position.in_tool] = (0, True)
        trace[P.tool.is_running] = (0, False)
        trace[P.operator.has_assembly] = (1, True)
        # Processed non-grabbed
        trace[P.operator.has_assembly] = (2, False)
        trace[P.cobot.has_assembly] = (2, True)
        trace[P.cobot.position.in_tool] = (2, True)
        trace[P.tool.is_running] = (2, True)
        self.evaluate(trace)

    def test_no_grab(self):
        trace = self.setup_trace()
        trace[P.operator.has_assembly] = (0, False)
        trace[P.cobot.has_assembly] = (0, True)
        trace[P.cobot.position.in_tool] = (0, True)
        trace[P.tool.is_running] = (0, False)
        self.evaluate(trace, expected=False)


class Test5T1(UCATest):
    uca_id = "UCA5-T-1"
    uca_desc = (
        "The Operator retrieves a Component while the Cobot is moving for the handover"
    )

    def test_occurs(self):
        trace = Trace()
        trace[P.operator.has_assembly] = (0, False)
        trace[P.cobot.has_assembly] = (0, True)
        trace[P.cobot.is_moving] = (0, True)
        trace[P.operator.has_assembly] = (1, True)
        self.evaluate(trace)

    def test_nominal(self):
        trace = Trace()
        trace[P.operator.has_assembly] = (0, False)
        trace[P.cobot.has_assembly] = (0, True)
        trace[P.cobot.is_moving] = (0, True)
        trace[P.cobot.is_moving] = (1, False)
        trace[P.operator.has_assembly] = (2, True)
        self.evaluate(trace, expected=False)

    def test_to_tool(self):
        trace = Trace()
        trace[P.operator.has_assembly] = (0, False)
        trace[P.cobot.has_assembly] = (0, True)
        trace[P.cobot.is_moving] = (0, True)
        trace[P.operator.has_assembly] = (1, True)
        self.evaluate(trace)

    def test_no_handover(self):
        trace = Trace()
        trace[P.operator.has_assembly] = (0, False)
        trace[P.cobot.has_assembly] = (0, False)
        trace[P.cobot.is_moving] = (0, True)
        trace[P.operator.has_assembly] = (1, True)
        self.evaluate(trace, expected=False)


class Test5T2(UCATest):
    uca_id = "UCA5-T-2"
    uca_desc = (
        "The Operator retrieves a Component before it has been secured for the handover"
    )

    def test_occurs(self):
        trace = Trace()
        trace[P.assembly.is_secured] = (0, False)
        trace[P.operator.has_assembly] = (0, False)
        trace[P.operator.has_assembly] = (1, True)
        self.evaluate(trace)

    def test_nominal(self):
        trace = Trace()
        trace[P.assembly.is_secured] = (0, True)
        trace[P.operator.has_assembly] = (0, False)
        trace[P.operator.has_assembly] = (1, True)
        self.evaluate(trace, expected=False)

    def test_occurs_once(self):
        trace = Trace()
        trace[P.assembly.is_secured] = (0, True)
        trace[P.operator.has_assembly] = (0, False)
        trace[P.operator.has_assembly] = (1, True)
        trace[P.operator.has_assembly] = (2, False)
        trace[P.assembly.is_secured] = (2, False)
        trace[P.operator.has_assembly] = (3, True)
        self.evaluate(trace)

    def test_occurs_nominal(self):
        trace = Trace()
        trace[P.assembly.is_secured] = (0, True)
        trace[P.operator.has_assembly] = (0, False)
        trace[P.operator.has_assembly] = (1, True)
        trace[P.operator.has_assembly] = (2, False)
        trace[P.operator.has_assembly] = (3, True)
        self.evaluate(trace, expected=False)


class Test7D1(UCATest):
    uca_id = "UCA7-D-1"
    uca_desc = "The Cobot does not hold the Component until it is secured"

    def test_occurs(self):
        trace = Trace()
        #
        trace[P.cobot.has_assembly] = (0, True)
        trace[P.cobot.position.in_bench] = (0, True)
        trace[P.cobot.position.in_bench] = (1, False)
        trace[P.cobot.position.in_tool] = (1, True)
        trace[P.cobot.has_assembly] = (2, False)
        self.evaluate(trace)

    def test_bench_release(self):
        trace = Trace()
        #
        trace[P.cobot.has_assembly] = (0, True)
        trace[P.cobot.position.in_bench] = (0, True)
        trace[P.cobot.has_assembly] = (1, False)
        self.evaluate(trace, expected=False)

    def test_round(self):
        trace = Trace()
        #
        trace[P.cobot.has_assembly] = (0, True)
        trace[P.cobot.position.in_bench] = (0, True)
        trace[P.cobot.position.in_bench] = (1, False)
        trace[P.cobot.position.in_tool] = (1, True)
        trace[P.cobot.position.in_tool] = (2, False)
        trace[P.cobot.position.in_bench] = (2, True)
        trace[P.cobot.has_assembly] = (3, False)
        self.evaluate(trace, expected=False)


class Test7N1(UCATest):
    uca_id = "UCA7-N-1"
    uca_desc = (
        "The Cobot does not grab the Component provided by the Operator when it is in handover position and "
        "available"
    )

    def test_occurs(self):
        trace = Trace()
        #
        trace[P.assembly.position.in_bench] = (0, True)
        trace[P.cobot.has_assembly] = (0, False)
        trace[P.cobot.position.in_bench] = (0, True)
        self.evaluate(trace)

    def test_cobot_grab(self):
        trace = Trace()
        #
        trace[P.assembly.position.in_bench] = (0, True)
        trace[P.cobot.has_assembly] = (0, True)
        trace[P.cobot.position.in_bench] = (0, True)
        self.evaluate(trace, expected=False)

    def test_cobot_away(self):
        trace = Trace()
        #
        trace[P.assembly.position.in_bench] = (0, True)
        trace[P.cobot.has_assembly] = (0, False)
        trace[P.cobot.position.in_tool] = (0, True)
        trace[P.cobot.position.in_bench] = (0, False)
        self.evaluate(trace, expected=False)

    def test_occurs_move(self):
        trace = Trace()
        #
        trace[P.assembly.position.in_bench] = (0, True)
        trace[P.cobot.has_assembly] = (0, False)
        trace[P.cobot.position.in_tool] = (0, True)
        trace[P.cobot.position.in_tool] = (5, False)
        trace[P.cobot.position.in_bench] = (5, True)
        trace[P.cobot.position.in_bench] = (10, False)
        trace[P.cobot.position.in_tool] = (10, True)
        self.evaluate(trace)

    def test_delayed_grab(self):
        trace = Trace()
        #
        trace[P.assembly.position.in_bench] = (0, True)
        trace[P.cobot.has_assembly] = (0, False)
        trace[P.cobot.position.in_tool] = (0, True)
        trace[P.cobot.position.in_tool] = (3, False)
        trace[P.cobot.position.in_bench] = (3, True)
        trace[P.cobot.has_assembly] = (5, True)
        self.evaluate(trace, expected=False)

    def test_multiple_occurrences(self):
        trace = Trace()
        #
        trace[P.assembly.position.in_bench] = (0, True)
        trace[P.cobot.has_assembly] = (0, False)
        trace[P.cobot.position.in_tool] = (0, True)
        trace[P.cobot.position.in_tool] = (5, True)
        trace[P.cobot.position.in_bench] = (5, True)
        trace[P.cobot.has_assembly] = (10, True)
        trace[P.cobot.position.in_bench] = (5, False)
        trace[P.cobot.position.in_tool] = (15, True)
        trace[P.cobot.has_assembly] = (16, False)
        trace[P.cobot.position.in_tool] = (20, False)
        trace[P.cobot.position.in_bench] = (20, True)
        self.evaluate(trace)


class Test7P1(UCATest):
    uca_id = "UCA7-P-1"
    uca_desc = "The Cobot grabs the Component while it has a high velocity"

    def setup_trace(self):
        trace = Trace()
        trace[P.constraints.cobot.velocity.in_bench] = (0, 10)
        trace[P.cobot.has_assembly] = (0, False)
        trace[P.cobot.velocity] = (0, 0)
        return trace

    def test_occurs(self):
        trace = self.setup_trace()
        #
        trace[P.constraints.cobot.velocity.in_bench] = (0, 10)
        trace[P.cobot.has_assembly] = (0, False)
        trace[P.cobot.velocity] = (0, False)
        trace[P.cobot.velocity] = (1, 20)
        trace[P.cobot.has_assembly] = (2, True)
        self.evaluate(trace)

    def test_slow(self):
        trace = self.setup_trace()
        #
        trace[P.constraints.cobot.velocity.in_bench] = (0, 10)
        trace[P.cobot.has_assembly] = (0, False)
        trace[P.cobot.velocity] = (0, False)
        trace[P.cobot.velocity] = (1, 5)
        trace[P.cobot.has_assembly] = (2, True)
        self.evaluate(trace, expected=False)

    def test_alternate_velocity(self):
        trace = self.setup_trace()
        #
        trace[P.constraints.cobot.velocity.in_bench] = (0, 10)
        trace[P.cobot.has_assembly] = (0, False)
        trace[P.cobot.velocity] = (0, False)
        trace[P.cobot.velocity] = (1, 5)
        trace[P.cobot.has_assembly] = (2, True)
        trace[P.cobot.has_assembly] = (10, False)
        trace[P.cobot.velocity] = (10, False)
        trace[P.cobot.velocity] = (11, 50)
        trace[P.cobot.has_assembly] = (12, True)
        self.evaluate(trace)

    def test_slowdown(self):
        trace = self.setup_trace()
        #
        trace[P.constraints.cobot.velocity.in_bench] = (0, 10)
        trace[P.cobot.has_assembly] = (0, False)
        trace[P.cobot.velocity] = (0, 20)
        trace[P.cobot.velocity] = (1, 5)
        trace[P.cobot.has_assembly] = (2, True)
        trace[P.cobot.velocity] = (3, 40)
        self.evaluate(trace, expected=False)


class Test7T1(UCATest):
    uca_id = "UCA7-T-1"
    uca_desc = (
        "The Cobot grabs a component before it has been released by the Operator",
    )

    def test_occurs(self):
        trace = Trace()
        trace[P.cobot.has_assembly] = (0, False)
        trace[P.cobot.has_assembly] = (1, True)
        trace[P.operator.has_assembly] = (0, True)
        self.evaluate(trace)

    def test_nominal(self):
        trace = Trace()
        trace[P.cobot.has_assembly] = (0, False)
        trace[P.cobot.has_assembly] = (1, True)
        trace[P.operator.has_assembly] = (0, False)
        self.evaluate(trace, expected=False)

    def test_releases(self):
        trace = Trace()
        trace[P.cobot.has_assembly] = (0, False)
        trace[P.cobot.has_assembly] = (2, True)
        trace[P.operator.has_assembly] = (0, True)
        trace[P.operator.has_assembly] = (1, False)
        self.evaluate(trace, expected=False)

    def test_operator_grabs(self):
        trace = Trace()
        trace[P.cobot.has_assembly] = (0, False)
        trace[P.cobot.has_assembly] = (1, True)
        trace[P.operator.has_assembly] = (0, False)
        trace[P.operator.has_assembly] = (1, True)
        self.evaluate(trace)

    def test_operator_releases(self):
        trace = Trace()
        trace[P.cobot.has_assembly] = (0, False)
        trace[P.cobot.has_assembly] = (1, True)
        trace[P.operator.has_assembly] = (0, True)
        trace[P.operator.has_assembly] = (1, False)
        self.evaluate(trace)


class Test8D1(UCATest):
    uca_id = "UCA8-D-1"
    uca_desc = (
        "The Cobot releases a Component too early during handover before it is secured"
    )

    def test_occurs(self):
        trace = Trace()
        #
        trace[P.assembly.is_secured] = (0, False)
        trace[P.cobot.has_assembly] = (0, True)
        trace[P.cobot.has_assembly] = (1, False)
        self.evaluate(trace)

    def test_secured(self):
        trace = Trace()
        #
        trace[P.assembly.is_secured] = (0, True)
        trace[P.cobot.has_assembly] = (0, True)
        trace[P.cobot.has_assembly] = (1, False)
        self.evaluate(trace, expected=False)

    def test_secured_release(self):
        trace = Trace()
        #
        trace[P.assembly.is_secured] = (0, False)
        trace[P.cobot.has_assembly] = (0, True)
        trace[P.assembly.is_secured] = (1, True)
        trace[P.cobot.has_assembly] = (2, False)
        self.evaluate(trace, expected=False)

    def test_occurs_once(self):
        trace = Trace()
        #
        trace[P.assembly.is_secured] = (0, True)
        trace[P.cobot.has_assembly] = (0, True)
        trace[P.cobot.has_assembly] = (1, False)
        trace[P.assembly.is_secured] = (10, False)
        trace[P.cobot.has_assembly] = (10, True)
        trace[P.cobot.has_assembly] = (11, False)
        self.evaluate(trace)


class Test8N1(UCATest):
    uca_id = "UCA8-N-1"
    uca_desc = "The Cobot does not releases the processed component when the operator is ready to retrieve it"

    def setup_trace(self):
        trace = Trace()
        trace[P.assembly.is_processed] = (0, False)
        trace[P.cobot.has_assembly] = (0, False)
        trace[P.cobot.position.in_bench] = (0, True)
        return trace

    def test_occurs_processed(self):
        trace = self.setup_trace()
        trace[P.assembly.is_processed] = (0, True)
        trace[P.cobot.has_assembly] = (0, True)
        trace[P.cobot.position.in_bench] = (0, True)
        self.evaluate(trace)

    def test_nominal(self):
        trace = self.setup_trace()
        trace[P.assembly.is_processed] = (0, True)
        trace[P.cobot.has_assembly] = (0, False)
        trace[P.cobot.position.in_bench] = (0, True)
        self.evaluate(trace, expected=False)

    def test_not_processed(self):
        trace = self.setup_trace()
        trace[P.assembly.is_processed] = (0, False)
        trace[P.cobot.has_assembly] = (0, False)
        trace[P.cobot.position.in_bench] = (0, True)
        self.evaluate(trace, expected=False)

    def test_wrong_release(self):
        trace = self.setup_trace()
        trace[P.assembly.is_processed] = (0, True)
        trace[P.cobot.has_assembly] = (0, False)
        trace[P.cobot.position.in_tool] = (0, True)
        self.evaluate(trace)


class Test8T1(UCATest):
    uca_id = "UCA8-T-1"
    uca_desc = "The Cobot releases the component during processing"

    def test_occurs(self):
        trace = Trace()
        trace[P.cobot.has_assembly] = (0, True)
        trace[P.cobot.position.in_tool] = (0, True)
        trace[P.tool.is_running] = (0, True)
        trace[P.cobot.has_assembly] = (1, False)
        self.evaluate(trace)

    def test_release_after(self):
        trace = Trace()
        trace[P.cobot.has_assembly] = (0, True)
        trace[P.cobot.position.in_tool] = (0, True)
        trace[P.tool.is_running] = (0, True)
        trace[P.tool.is_running] = (1, False)
        trace[P.cobot.has_assembly] = (2, False)
        self.evaluate(trace, expected=False)

    def test_release_bench(self):
        trace = Trace()
        trace[P.cobot.has_assembly] = (0, True)
        trace[P.cobot.position.in_bench] = (0, True)
        trace[P.cobot.position.in_tool] = (0, False)
        trace[P.tool.is_running] = (0, True)
        trace[P.cobot.has_assembly] = (1, False)
        self.evaluate(trace, expected=False)

    def test_release_before(self):
        trace = Trace()
        trace[P.cobot.has_assembly] = (0, True)
        trace[P.cobot.position.in_tool] = (0, True)
        trace[P.cobot.has_assembly] = (1, False)
        trace[P.tool.is_running] = (0, False)
        trace[P.tool.is_running] = (2, True)
        self.evaluate(trace, expected=False)


class Test9N1(UCATest):
    uca_id = "UCA9-N-1"
    uca_desc = "The Cobot does not reach the target position"

    def test_occurs(self):
        trace = Trace()
        trace[P.cobot.has_target] = (0, True)
        trace[P.cobot.reaches_target] = (0, False)
        self.evaluate(trace)

    def test_reaches_target(self):
        trace = Trace()
        trace[P.cobot.has_target] = (0, True)
        trace[P.cobot.reaches_target] = (1, True)
        trace[P.cobot.has_target] = (1, False)
        self.evaluate(trace, expected=False)

    def test_delayed_reach(self):
        trace = Trace()
        trace[P.cobot.has_target] = (0, True)
        trace[P.cobot.reaches_target] = (25000, True)
        self.evaluate(trace, expected=False)

    def test_multiple_targets(self):
        trace = Trace()
        trace[P.cobot.has_target] = (0, True)
        trace[P.cobot.reaches_target] = (1, True)
        trace[P.cobot.has_target] = (2, False)
        trace[P.cobot.has_target] = (3, True)
        trace[P.cobot.reaches_target] = (4, True)
        trace[P.cobot.has_target] = (5, False)
        self.evaluate(trace, expected=False)

    def test_multiple_occurs(self):
        trace = Trace()
        trace[P.cobot.has_target] = (0, True)
        trace[P.cobot.reaches_target] = (1, True)
        trace[P.cobot.has_target] = (1, False)
        trace[P.cobot.reaches_target] = (2, False)
        trace[P.cobot.has_target] = (3, True)
        trace[P.cobot.has_target] = (5, False)
        self.evaluate(trace)

    def test_multiple_passes(self):
        trace = Trace()
        trace[P.cobot.has_target] = (0, True)
        trace[P.cobot.reaches_target] = (1, True)
        trace[P.cobot.has_target] = (1, False)
        trace[P.cobot.reaches_target] = (2, False)
        trace[P.cobot.has_target] = (3, True)
        trace[P.cobot.reaches_target] = (4, True)
        trace[P.cobot.has_target] = (5, False)
        trace[P.cobot.reaches_target] = (5, False)
        self.evaluate(trace, expected=False)

    def test_target_loss(self):
        trace = Trace()
        trace[P.cobot.reaches_target] = (0, False)
        trace[P.cobot.has_target] = (0, True)
        trace[P.cobot.has_target] = (2, False)
        self.evaluate(trace)


class Test9P2(UCATest):
    uca_id = "UCA9-P-2"
    uca_desc = "The Cobot moves position while its path is obstructed"

    def setup_trace(self):
        trace = Trace()
        trace[P.cobot.is_moving] = (0, False)
        # FIXME Obstruction detected from operator position trace[P.workspace.has_obstruction] = (0, False)
        trace[P.operator.position.in_workspace] = (0, False)
        return trace

    def test_occurs(self):
        trace = self.setup_trace()
        trace[P.cobot.is_moving] = (0, True)
        trace[P.operator.position.in_workspace] = (0, True)
        self.evaluate(trace)

    def test_obstruction_leaves(self):
        trace = self.setup_trace()
        trace[P.operator.position.in_workspace] = (0, True)
        trace[P.operator.position.in_workspace] = (1, False)
        trace[P.cobot.is_moving] = (1, True)
        self.evaluate(trace, expected=False)


class Test9P3(UCATest):
    uca_id = "UCA9-P-3"
    uca_desc = "The Cobot moves position while it has an unsecured part"

    def test_occurs(self):
        trace = Trace()
        trace[P.assembly.is_secured] = (0, False)
        trace[P.cobot.has_assembly] = (0, True)
        trace[P.cobot.is_moving] = (0, True)
        self.evaluate(trace)

    def test_secured(self):
        trace = Trace()
        trace[P.assembly.is_secured] = (0, True)
        trace[P.cobot.has_assembly] = (0, True)
        trace[P.cobot.is_moving] = (0, True)
        self.evaluate(trace, expected=False)

    def test_secured_on_move(self):
        trace = Trace()
        trace[P.assembly.is_secured] = (0, False)
        trace[P.cobot.has_assembly] = (0, True)
        trace[P.cobot.is_moving] = (0, False)
        trace[P.assembly.is_secured] = (1, True)
        trace[P.cobot.is_moving] = (2, True)
        self.evaluate(trace, expected=False)

    def test_no_assembly(self):
        trace = Trace()
        trace[P.assembly.is_secured] = (0, False)
        trace[P.cobot.has_assembly] = (0, False)
        trace[P.cobot.is_moving] = (0, True)
        self.evaluate(trace, expected=False)

    def test_no_move(self):
        trace = Trace()
        trace[P.assembly.is_secured] = (0, False)
        trace[P.cobot.has_assembly] = (0, True)
        trace[P.cobot.is_moving] = (0, False)
        self.evaluate(trace, expected=False)


class Test9T1(UCATest):
    uca_id = "UCA9-T-1"
    uca_desc = (
        "The Cobot moves to processing position before it has grabbed a Component"
    )

    def test_occurs(self):
        trace = Trace()
        trace[P.cobot.has_assembly] = (0, False)
        trace[P.cobot.is_moving] = (0, True)
        trace[P.cobot.position.in_bench] = (0, True)
        trace[P.cobot.position.in_bench] = (1, False)
        trace[P.cobot.position.in_tool] = (1, True)
        self.evaluate(trace)

    def test_has_assembly(self):
        trace = Trace()
        trace[P.cobot.has_assembly] = (0, True)
        trace[P.cobot.is_moving] = (0, True)
        trace[P.cobot.position.in_bench] = (0, True)
        trace[P.cobot.position.in_bench] = (1, False)
        trace[P.cobot.position.in_tool] = (1, True)
        self.evaluate(trace, expected=False)

    def test_occurs_from_workspace(self):
        trace = Trace()
        trace[P.cobot.has_assembly] = (0, False)
        trace[P.cobot.is_moving] = (0, True)
        trace[P.cobot.position.in_workspace] = (0, True)
        trace[P.cobot.position.in_workspace] = (1, False)
        trace[P.cobot.position.in_tool] = (1, True)
        self.evaluate(trace)

    def test_valid_move(self):
        trace = Trace()
        trace[P.cobot.has_assembly] = (0, False)
        trace[P.cobot.is_moving] = (0, False)
        trace[P.cobot.is_moving] = (1, True)
        trace[P.cobot.position.in_tool] = (0, True)
        trace[P.cobot.position.in_tool] = (1, False)
        trace[P.cobot.position.in_workspace] = (1, True)
        trace[P.cobot.position.in_workspace] = (2, False)
        trace[P.cobot.position.in_bench] = (2, True)
        self.evaluate(trace, expected=False)

    def test_assembly_pickup(self):
        trace = Trace()
        trace[P.cobot.has_assembly] = (0, False)
        trace[P.cobot.is_moving] = (0, False)
        trace[P.cobot.is_moving] = (1, True)
        trace[P.cobot.position.in_tool] = (0, True)
        trace[P.cobot.position.in_tool] = (1, False)
        trace[P.cobot.position.in_bench] = (1, True)
        trace[P.cobot.position.in_bench] = (2, False)
        trace[P.cobot.has_assembly] = (1, True)
        trace[P.cobot.position.in_workspace] = (2, True)
        trace[P.cobot.position.in_workspace] = (3, False)
        trace[P.cobot.position.in_tool] = (3, True)
        self.evaluate(trace, expected=False)


class Test9T2(UCATest):
    uca_id = "UCA9-T-2"
    uca_desc = "The Cobot moves position while grabbing a Component"

    def test_occurs(self):
        trace = Trace()
        trace[P.cobot.is_moving] = (0, True)
        trace[P.cobot.has_assembly] = (0, False)
        trace[P.cobot.has_assembly] = (1, True)
        self.evaluate(trace)

    def test_no_grab(self):
        trace = Trace()
        trace[P.cobot.is_moving] = (0, True)
        trace[P.cobot.has_assembly] = (0, False)
        self.evaluate(trace, expected=False)

    def test_nominal(self):
        trace = Trace()
        trace[P.cobot.is_moving] = (0, False)
        trace[P.cobot.has_assembly] = (0, False)
        trace[P.cobot.has_assembly] = (1, True)
        trace[P.cobot.is_moving] = (2, True)
        self.evaluate(trace, expected=False)


class Test10P1(UCATest):
    uca_id = "UCA10-P-1"
    uca_desc = "The Cobot processes a Component that is damaged"

    def setup_trace(self):
        trace = Trace()
        trace[P.assembly.is_damaged] = (0, False)
        trace[P.assembly.under_processing] = (0, False)
        return trace

    def test_occurs(self):
        trace = self.setup_trace()
        trace[P.assembly.is_damaged] = (0, True)
        trace[P.assembly.under_processing] = (0, True)
        self.evaluate(trace)

    def test_occurs_multiple(self):
        trace = self.setup_trace()
        trace[P.assembly.is_damaged] = (0, False)
        trace[P.assembly.under_processing] = (0, True)
        trace[P.assembly.under_processing] = (1, False)
        trace[P.assembly.is_damaged] = (2, True)
        trace[P.assembly.under_processing] = (2, True)
        trace[P.assembly.under_processing] = (3, False)
        self.evaluate(trace)

    def test_damaged_during(self):
        trace = self.setup_trace()
        trace[P.assembly.is_damaged] = (0, False)
        trace[P.assembly.under_processing] = (0, True)
        trace[P.assembly.is_damaged] = (1, True)
        self.evaluate(trace)

    def test_nominal(self):
        trace = self.setup_trace()
        trace[P.assembly.is_damaged] = (0, False)
        trace[P.assembly.under_processing] = (0, True)
        self.evaluate(trace, expected=False)

    def test_damaged_after(self):
        trace = self.setup_trace()
        trace[P.assembly.is_damaged] = (0, False)
        trace[P.assembly.under_processing] = (0, True)
        trace[P.assembly.under_processing] = (1, False)
        trace[P.assembly.is_damaged] = (2, True)
        self.evaluate(trace, expected=False)


class Test10P2(UCATest):
    uca_id = "UCA10-P-2"
    uca_desc = (
        "The Cobot processes a Component when the configured process is incompatible"
    )

    def setup_trace(self):
        trace = Trace()
        trace[P.assembly.is_valid] = (0, False)
        trace[P.assembly.under_processing] = (0, False)
        return trace

    def test_occurs(self):
        trace = self.setup_trace()
        trace[P.assembly.is_valid] = (0, False)
        trace[P.assembly.under_processing] = (0, True)
        self.evaluate(trace)

    def test_occurs_multiple(self):
        trace = self.setup_trace()
        trace[P.assembly.is_valid] = (0, True)
        trace[P.assembly.under_processing] = (0, True)
        trace[P.assembly.under_processing] = (1, False)
        trace[P.assembly.is_valid] = (2, False)
        trace[P.assembly.under_processing] = (2, True)
        self.evaluate(trace)

    def test_valid_during(self):
        trace = self.setup_trace()
        trace[P.assembly.is_valid] = (0, True)
        trace[P.assembly.under_processing] = (0, True)
        trace[P.assembly.is_valid] = (1, False)
        self.evaluate(trace)

    def test_nominal(self):
        trace = self.setup_trace()
        trace[P.assembly.is_valid] = (0, True)
        trace[P.assembly.under_processing] = (0, True)
        self.evaluate(trace, expected=False)

    def test_invalid_after(self):
        trace = self.setup_trace()
        trace[P.assembly.is_valid] = (0, True)
        trace[P.assembly.under_processing] = (0, True)
        trace[P.assembly.under_processing] = (1, False)
        trace[P.assembly.is_valid] = (2, False)
        self.evaluate(trace, expected=False)


class Test10P3(UCATest):
    uca_id = "UCA10-P-3"
    uca_desc = "The Cobot starts the processing when no Component is currently held"

    def setup_trace(self):
        trace = Trace()
        trace[P.cobot.has_assembly] = (0, False)
        trace[P.cobot.position.in_tool] = (0, True)
        trace[P.tool.is_running] = (0, False)
        return trace

    def test_occurs(self):
        trace = self.setup_trace()
        trace[P.cobot.has_assembly] = (0, False)
        trace[P.cobot.position.in_tool] = (0, True)
        trace[P.tool.is_running] = (0, False)
        trace[P.tool.is_running] = (1, True)
        self.evaluate(trace)

    def test_nominal(self):
        trace = self.setup_trace()
        trace[P.cobot.has_assembly] = (0, True)
        trace[P.cobot.position.in_tool] = (0, True)
        trace[P.tool.is_running] = (0, False)
        trace[P.tool.is_running] = (1, True)
        self.evaluate(trace, expected=False)

    def test_drop_after(self):
        trace = self.setup_trace()
        trace[P.cobot.has_assembly] = (0, True)
        trace[P.cobot.position.in_tool] = (0, True)
        trace[P.tool.is_running] = (0, False)
        trace[P.tool.is_running] = (1, True)
        trace[P.cobot.has_assembly] = (1, False)
        self.evaluate(trace, expected=False)

    def test_drop_before(self):
        trace = self.setup_trace()
        trace[P.cobot.has_assembly] = (0, True)
        trace[P.cobot.position.in_tool] = (0, True)
        trace[P.tool.is_running] = (0, False)
        trace[P.cobot.has_assembly] = (1, False)
        trace[P.tool.is_running] = (2, True)
        self.evaluate(trace)


class Test10P4(UCATest):
    uca_id = "UCA10-P-4"
    uca_desc = "The Cobot processes a Component when minimum separation requirements are not met"

    def setup_trace(self):
        trace = Trace()
        trace[P.assembly.under_processing] = (0, False)
        trace[P.constraints.tool.distance.operation] = (0, 10)
        trace[P.tool.distance] = (0, 0)
        return trace

    def test_occurs(self):
        trace = self.setup_trace()
        trace[P.assembly.under_processing] = (0, True)
        trace[P.constraints.tool.distance.operation] = (0, 10)
        trace[P.tool.distance] = (0, 0)
        self.evaluate(trace)

    def test_nominal(self):
        trace = self.setup_trace()
        trace[P.assembly.under_processing] = (0, True)
        trace[P.constraints.tool.distance.operation] = (0, 10)
        trace[P.tool.distance] = (0, 20)
        self.evaluate(trace, expected=False)

    def test_leaves(self):
        trace = self.setup_trace()
        trace[P.assembly.under_processing] = (0, False)
        trace[P.constraints.tool.distance.operation] = (0, 10)
        trace[P.tool.distance] = (0, 0)
        trace[P.assembly.under_processing] = (1, True)
        trace[P.tool.distance] = (0, 20)
        self.evaluate(trace, expected=False)

    def test_enters(self):
        trace = self.setup_trace()
        trace[P.assembly.under_processing] = (0, True)
        trace[P.constraints.tool.distance.operation] = (0, 10)
        trace[P.tool.distance] = (0, 20)
        trace[P.tool.distance] = (1, 1)
        self.evaluate(trace)

    def test_multiple(self):
        trace = self.setup_trace()
        trace[P.assembly.under_processing] = (0, True)
        trace[P.constraints.tool.distance.operation] = (0, 10)
        trace[P.tool.distance] = (0, 20)
        trace[P.assembly.under_processing] = (1, False)
        trace[P.tool.distance] = (1, 0)
        trace[P.tool.distance] = (2, 60)
        trace[P.assembly.under_processing] = (3, True)
        self.evaluate(trace, expected=False)


class Test10P5(UCATest):
    uca_id = "UCA10-P-5"
    uca_desc = "The Cobot processes a Component when personnel is present in the processing area"

    def setup_trace(self):
        trace = Trace()
        trace[P.assembly.under_processing] = (0, False)
        trace[P.operator.position.in_workspace] = (0, True)
        return trace

    def test_occurs(self):
        trace = self.setup_trace()
        trace[P.assembly.under_processing] = (0, True)
        trace[P.operator.position.in_bench] = (0, False)
        trace[P.operator.position.in_workspace] = (0, True)
        self.evaluate(trace)

    def test_operator_enters(self):
        trace = self.setup_trace()
        trace[P.assembly.under_processing] = (0, True)
        trace[P.operator.position.in_bench] = (0, True)
        trace[P.operator.position.in_bench] = (1, False)
        trace[P.operator.position.in_workspace] = (1, True)
        self.evaluate(trace)

    def test_operator_leaves(self):
        trace = self.setup_trace()
        trace[P.assembly.under_processing] = (0, True)
        trace[P.operator.position.in_bench] = (0, False)
        trace[P.operator.position.in_workspace] = (0, True)
        trace[P.operator.position.in_workspace] = (1, False)
        trace[P.operator.position.in_bench] = (1, True)
        self.evaluate(trace)

    def test_tool_stops(self):
        trace = self.setup_trace()
        trace[P.assembly.under_processing] = (0, True)
        trace[P.operator.position.in_bench] = (0, True)
        trace[P.assembly.under_processing] = (1, False)
        trace[P.operator.position.in_bench] = (1, False)
        trace[P.operator.position.in_workspace] = (1, True)
        self.evaluate(trace, expected=False)

    def test_nominal(self):
        trace = self.setup_trace()
        trace[P.assembly.under_processing] = (0, True)
        trace[P.operator.position.in_bench] = (0, True)
        self.evaluate(trace, expected=False)


class Test10T1(UCATest):
    uca_id = "UCA10-T-1"
    uca_desc = "The Cobot processes a component before it has been configured"

    def setup_trace(self):
        trace = Trace()
        trace[P.assembly.under_processing] = (0, False)
        trace[P.controller.is_configured] = (0, False)
        return trace

    def test_occurs(self):
        trace = self.setup_trace()
        trace[P.assembly.under_processing] = (0, True)
        trace[P.controller.is_configured] = (0, False)
        self.evaluate(trace)

    def test_nominal(self):
        trace = self.setup_trace()
        trace[P.assembly.under_processing] = (0, True)
        trace[P.controller.is_configured] = (0, True)
        self.evaluate(trace, expected=False)

    def test_no_process(self):
        trace = self.setup_trace()
        trace[P.assembly.under_processing] = (0, False)
        trace[P.controller.is_configured] = (0, False)
        self.evaluate(trace, expected=False)

    def test_remove_configuration(self):
        trace = self.setup_trace()
        trace[P.assembly.under_processing] = (0, True)
        trace[P.controller.is_configured] = (0, True)
        trace[P.assembly.under_processing] = (1, True)
        trace[P.controller.is_configured] = (1, False)
        self.evaluate(trace, expected=False)

    def test_late_configure(self):
        trace = self.setup_trace()
        trace[P.assembly.under_processing] = (0, False)
        trace[P.controller.is_configured] = (0, False)
        trace[P.assembly.under_processing] = (1, True)
        trace[P.controller.is_configured] = (1, True)
        self.evaluate(trace, expected=False)


class Test10T3(UCATest):
    uca_id = "UCA10-T-3"
    uca_desc = "The Cobot processes a component before it has reached the required position and velocity"

    def setup_trace(self):
        trace = Trace()
        trace[P.constraints.cobot.velocity.in_tool] = (0, 1)
        trace[P.assembly.under_processing] = (0, False)
        trace[P.cobot.velocity] = (0, 10)
        return trace

    def test_occurs(self):
        trace = self.setup_trace()
        trace[P.constraints.cobot.velocity.in_tool] = (0, 1)
        trace[P.assembly.under_processing] = (0, True)
        trace[P.cobot.velocity] = (0, 10)
        self.evaluate(trace)

    def test_nominal(self):
        trace = self.setup_trace()
        trace[P.constraints.cobot.velocity.in_tool] = (0, 1)
        trace[P.assembly.under_processing] = (0, True)
        trace[P.cobot.velocity] = (0, 0)
        self.evaluate(trace, expected=False)

    def test_no_process(self):
        trace = self.setup_trace()
        trace[P.constraints.cobot.velocity.in_tool] = (0, 1)
        trace[P.assembly.under_processing] = (0, False)
        trace[P.cobot.velocity] = (0, 10)
        self.evaluate(trace, expected=False)

    def test_speeds_after(self):
        trace = self.setup_trace()
        trace[P.constraints.cobot.velocity.in_tool] = (0, 1)
        trace[P.assembly.under_processing] = (0, True)
        trace[P.cobot.velocity] = (0, 0)
        trace[P.assembly.under_processing] = (1, False)
        trace[P.cobot.velocity] = (1, 10)
        self.evaluate(trace, expected=False)

    def test_speeds_up(self):
        trace = self.setup_trace()
        trace[P.constraints.cobot.velocity.in_tool] = (0, 1)
        trace[P.assembly.under_processing] = (0, True)
        trace[P.cobot.velocity] = (0, 0)
        trace[P.cobot.velocity] = (1, 10)
        self.evaluate(trace)


class Test10T4(UCATest):
    uca_id = "UCA10-T-4"
    uca_desc = "The Cobot processes a component before the Component been secured"

    def setup_trace(self):
        trace = Trace()
        trace[P.assembly.under_processing] = (0, False)
        trace[P.assembly.is_secured] = (0, False)
        return trace

    def test_occurs(self):
        trace = self.setup_trace()
        trace[P.assembly.under_processing] = (0, True)
        trace[P.assembly.is_secured] = (0, False)
        self.evaluate(trace)

    def test_nominal(self):
        trace = self.setup_trace()
        trace[P.assembly.under_processing] = (0, True)
        trace[P.assembly.is_secured] = (0, True)
        self.evaluate(trace, expected=False)

    def test_release(self):
        trace = self.setup_trace()
        trace[P.assembly.under_processing] = (0, True)
        trace[P.assembly.is_secured] = (0, True)
        trace[P.assembly.under_processing] = (1, False)
        trace[P.assembly.is_secured] = (1, False)
        self.evaluate(trace, expected=False)


class Test11N1(UCATest):
    uca_id = "UCA11-N-1"
    uca_desc = "The Operator does not configure the process before operation"

    def test_occurs_move(self):
        trace = Trace()
        trace[P.controller.is_configured] = (0, False)
        trace[P.cobot.has_assembly] = (0, False)
        trace[P.cobot.is_moving] = (0, True)
        self.evaluate(trace)

    def test_occurs_grab(self):
        trace = Trace()
        trace[P.controller.is_configured] = (0, False)
        trace[P.cobot.has_assembly] = (0, False)
        trace[P.cobot.has_assembly] = (1, True)
        trace[P.cobot.is_moving] = (0, False)
        self.evaluate(trace)

    def test_occurs_release(self):
        trace = Trace()
        trace[P.controller.is_configured] = (0, False)
        trace[P.cobot.has_assembly] = (0, True)
        trace[P.cobot.has_assembly] = (1, False)
        trace[P.cobot.is_moving] = (0, False)
        self.evaluate(trace)

    def test_nominal(self):
        trace = Trace()
        trace[P.controller.is_configured] = (0, True)
        trace[P.cobot.has_assembly] = (0, True)
        trace[P.cobot.has_assembly] = (1, False)
        trace[P.cobot.has_assembly] = (2, True)
        trace[P.cobot.is_moving] = (0, True)
        trace[P.cobot.is_moving] = (1, False)
        self.evaluate(trace, expected=False)

    def test_delayed_configuration(self):
        trace = Trace()
        trace[P.controller.is_configured] = (0, False)
        trace[P.controller.is_configured] = (10, True)
        trace[P.cobot.has_assembly] = (0, True)
        trace[P.cobot.has_assembly] = (15, False)
        trace[P.cobot.has_assembly] = (20, True)
        trace[P.cobot.is_moving] = (0, False)
        trace[P.cobot.is_moving] = (10, True)
        self.evaluate(trace, expected=False)

    def test_never_configured(self):
        trace = Trace()
        trace[P.controller.is_configured] = (0, False)
        trace[P.cobot.has_assembly] = (0, True)
        trace[P.cobot.is_moving] = (0, False)
        trace[P.operator.position.in_bench] = (0, True)
        trace[P.operator.position.in_bench] = (10, False)
        trace[P.operator.position.in_tool] = (10, True)
        trace[P.operator.position.in_tool] = (20, True)
        trace[P.operator.position.in_workspace] = (20, True)
        self.evaluate(trace, expected=False)


if __name__ == "__main__":
    pytest.main()
