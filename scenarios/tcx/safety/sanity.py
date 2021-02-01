from csi.monitor import Monitor, P
from csi.safety.stpa import SafetyCondition

sanity_checks = set()


def __register_check(description, condition):
    """Register a new unsafe control action"""
    global sanity_checks
    sanity_checks.add(SafetyCondition(description, condition))


__register_check("The tool starts inactive", P.tool.is_running)

# Assembly follows whoever holds it

# Only one assembly in the world

# Assembly is moving implies -> Exists a manipulator which moves and has the assembly

# Only one arm in the world

# Assembly is held -> One of the manipulators has the assembly

# Operator provides assembly -> At bench and has assembly

# Operator provides assembly -> Operator does not have the assembly after


sanity_monitor = Monitor({s.condition for s in sanity_checks})
