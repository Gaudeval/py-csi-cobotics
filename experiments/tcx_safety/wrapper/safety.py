"""
Formalisation of STPA analysis results for monitoring tcx industrial cell.

"""
import operator

from functools import reduce

from mtfl import BOT

from csi.situation import Monitor
from csi import Hazard, UnsafeControlAction

from .monitor import P, Entities

# TODO Formalise and evaluate the following sanity checks for all runs
# - The tool starts inactive
# - Assembly follows whoever holds it
# - Only one assembly in the world
# - Assembly is moving implies -> Exists a manipulator which moves and has the assembly
# - Only one arm in the world
# - Assembly is held -> One of the manipulators has the assembly
# - Operator provides assembly -> At bench and has assembly
# - Operator provides assembly -> Operator does not have the assembly after


# Capture a list of selected unsafe control actions relevant to the Digital Twin
unsafe_control_actions = set()


__TOLERANCE = 5.0


def __register_uca(uid, description, condition):
    """Register a new unsafe control action"""
    unsafe_control_actions.add(UnsafeControlAction(uid, condition, description))


__register_uca(
    "UCA1-D-1",
    "Training ends before Specialised Operator is fully familiarised with safety policies and/or"
    "equipment",
    BOT,
)

__register_uca(
    "UCA1-N-1",
    "No training is delivered to the Specialised Operator working with a Cobot",
    BOT,
)

__register_uca(
    "UCA1-N-2",
    "Training is not re-assessed for the Specialised Operator when changes occurred in the "
    "Equipment and/or procedures",
    BOT,
)

__register_uca(
    "UCA1-T-1",
    "Updated procedures are circulated after changes have taken place in the work areas",
    BOT,
)

__register_uca(
    "UCA2-N-1",
    "The Maintenance Schedule is not provided when the Specialised Operator is in charge of the "
    "Cobot maintenance and configuration",
    BOT,
)

__register_uca(
    "UCA3-D-1",
    "Training ends before Operator is fully familiarised with safety policies and/or the Equipment",
    BOT,
)

__register_uca(
    "UCA3-N-1",
    "The Operator is unaware of safe operational conditions when operating the Equipment",
    BOT,
)

__register_uca(
    "UCA3-T-1",
    "Updated procedures are circulated after changes have taken place in the work areas",
    BOT,
)

__register_uca(
    "UCA4-D-1",
    "The Operator keeps holding on to a secured Component while the Cobot is moving to another "
    "position.",
    (P.operator.has_assembly & P.cobot.has_assembly & P.cobot.is_moving).eventually(),
)

__register_uca(
    "UCA4-D-2",
    "The Operator releases a Component before it is secured",
    (P.operator.releases_assembly & ~P.assembly.is_secured).eventually(),
)

__register_uca(
    "UCA4-N-1",
    "The Operator does not provide a Component when one is available and the Cobot is ready",
    ~(
        (P.operator.has_assembly & (P.cobot.position.in_bench) & ~P.cobot.has_assembly)
        .implies(P.operator.provides_assembly.eventually())
        .always()
    ),
)

__register_uca(
    "UCA4-P-1",
    "The Operator provides a Component when the controller has been configured for a different "
    "Component",
    (P.operator.provides_assembly & (~P.assembly.is_valid)).eventually(),
)

__register_uca(
    "UCA4-P-2",
    "The Operator provides an unprepared or damaged Component",
    (P.operator.provides_assembly & P.assembly.is_damaged).eventually(),
)

__register_uca(
    "UCA4-P-3",
    "The Operator provides a Component in the wrong position or orientation",
    (P.operator.provides_assembly & ~P.assembly.is_orientation_valid).eventually(),
)

__register_uca(
    "UCA4-T-1",
    "The Operator provides a Component to the Cobot while another is being processed",
    (P.assembly.under_processing & P.operator.provides_assembly).eventually(),
)

__register_uca(
    "UCA4-T-2",
    "The Operator provides a Component to the Cobot while it is approaching for the handover",
    (
        P.operator.provides_assembly
        & (P.cobot.is_moving).until(P.cobot.position.in_bench)
    ).eventually(),
)

__register_uca(
    "UCA4-T-3",
    "The Operator provides a Component when the controller has not been configured",
    (P.operator.provides_assembly & (~P.controller.is_configured)).eventually(),
)

__register_uca(
    "UCA5-D-1",
    "The Operator releases a Component before he has secured it",
    (P.operator.releases_assembly & (~P.assembly.is_secured)).eventually(),
)

__register_uca(
    "UCA5-N-1",
    "The Operator does not collect the processed Component",
    BOT,  # TODO Formalise
)

__register_uca(
    "UCA5-P-1",
    "The Operator retrieves the Component while it is secured by the Cobot",
    (
        P.operator.grabs_assembly & P.cobot.has_assembly & P.assembly.is_secured
    ).eventually(),
)

__register_uca(
    "UCA5-P-2",
    "The Operator retrieves the Component while it is being processed.",
    (P.operator.grabs_assembly & P.assembly.under_processing).eventually(),
)

__register_uca(
    "UCA5-P-3",
    "The Operator retrieves a Component before it has been processed",
    ~(
        (~P.operator.grabs_assembly.eventually())
        | (~P.operator.has_assembly).until(P.assembly.is_processed)
    ).always(),
)

__register_uca(
    "UCA5-T-1",
    "The Operator retrieves a Component while the Cobot is moving for the handover",
    (P.operator.grabs_assembly & P.cobot.is_moving & P.cobot.has_assembly).eventually(),
)

__register_uca(
    "UCA5-T-2",
    "The Operator retrieves a Component before it has been secured for the handover",
    (P.operator.grabs_assembly & ~P.assembly.is_secured).eventually(),
)

__register_uca(
    "UCA5-T-3", "The Operator retrieves a Component before it is safe to handle", BOT
)

__register_uca(
    "UCA6-N-1",
    "The Operator fails to interrupt the process when safe operational conditions are not met",
    BOT,
)

__register_uca(
    "UCA6-P-1",
    "The Operator interrupts the process when the Cobot is under maintenance",
    BOT,
)

__register_uca(
    "UCA6-P-2", "The Operator interrupts the process when no operation is underway", BOT
)

__register_uca(
    "UCA6-P-3",
    "The Operator interrupts the process while safe operational conditions are met",
    BOT,
)

__register_uca(
    "UCA7-D-1",
    "The Cobot does not hold the Component until it is secured",
    (P.cobot.releases_assembly & P.assembly.needs_secured).eventually(),
)

__register_uca(
    "UCA7-N-1",
    "The Cobot does not grab the Component provided by the Operator when it is in handover position"
    " and available",
    ~(
        (
            (~P.cobot.has_assembly)
            & P.cobot.position.in_bench
            & P.assembly.position.in_bench
            & (~P.assembly.is_processed)
        )
        .implies(P.cobot.has_assembly.eventually())
        .always()
    ),
)

__register_uca(
    "UCA7-P-1",
    "The Cobot grabs the Component while it has a high velocity",
    (
        P.cobot.grabs_assembly
        & (P.cobot.velocity.gt(P.constraints.cobot.velocity.in_bench, __TOLERANCE))
    ).eventually(),
)

__register_uca(
    "UCA7-P-2", "The Cobot grabs a Component while the Effector is already in use", BOT
)

__register_uca(
    "UCA7-P-3",
    "The Cobot grabs a damaged or unprepared Component",
    (P.cobot.grabs_assembly & P.assembly.is_damaged).eventually(),  # TODO Test
)

__register_uca(
    "UCA7-P-4",
    "The Cobot grabs a component in the wrong orientation or position",
    (
        P.cobot.grabs_assembly & (~P.assembly.is_orientation_valid)
    ).eventually(),  # TODO Test
)

__register_uca(
    "UCA7-T-1",
    "The Cobot grabs a component before it has been released by the Operator",
    (
        P.cobot.grabs_assembly
        & (
            P.operator.grabs_assembly
            | P.operator.releases_assembly
            | P.operator.has_assembly
        )
    ).eventually(),
)

__register_uca(
    "UCA8-D-1",
    "The Cobot releases a Component too early during handover before it is secured",
    (P.cobot.releases_assembly & (~P.assembly.is_secured)).eventually(),
)

__register_uca(
    "UCA8-N-1",
    "The Cobot does not releases the processed component when the operator is ready to retrieve it",
    ~P.assembly.is_delivered,
)

__register_uca(
    "UCA8-T-1",
    "The Cobot releases the component during processing",
    (
        P.tool.is_running & P.cobot.position.in_tool & P.cobot.releases_assembly
    ).eventually(),
)

__register_uca(
    "UCA8-T-2", "The Cobot releases the component before it is safe to handle", BOT
)

__register_uca(
    "UCA9-N-1",
    "The Cobot does not reach the target position",
    ~(
        P.cobot.has_target.implies(
            (P.cobot.has_target & P.cobot.is_moving).weak_until(P.cobot.reaches_target)
        ).always()
    ),
)

__register_uca("UCA9-P-1", "The Cobot moves position while under maintenance", BOT)

__register_uca(
    "UCA9-P-2",
    "The Cobot moves position while its path is obstructed",
    (P.workspace.has_obstruction & P.cobot.is_moving).eventually(),
)

__register_uca(
    "UCA9-P-3",
    "The Cobot moves position while it has an unsecured part",
    (P.cobot.is_moving & P.cobot.has_assembly & (~P.assembly.is_secured)).eventually(),
)


# FIXME Triggers incorrectly if leaving the tool position without assembly
__register_uca(
    "UCA9-T-1",
    "The Cobot moves to processing position before it has grabbed a Component",
    (
        P.cobot.is_moving & ((P.cobot.position.in_tool) >> 1) & (~P.cobot.has_assembly)
    ).eventually(),
)

__register_uca(
    "UCA9-T-2",
    "The Cobot moves position while grabbing a Component",
    (P.cobot.grabs_assembly & P.cobot.is_moving).eventually(),
)

__register_uca(
    "UCA10-D-1",
    "The Cobot stops processing the part before the process is complete",
    BOT,
)

__register_uca(
    "UCA10-D-2",
    "The Cobot keeps processing the Component after the end of the configured process",
    BOT,
)

__register_uca(
    "UCA10-D-3", "The Cobot processes the part beyond the processing requirements", BOT
)

__register_uca(
    "UCA10-P-1",
    "The Cobot processes a Component that is damaged",
    (P.assembly.under_processing & P.assembly.is_damaged).eventually(),
)

__register_uca(
    "UCA10-P-2",
    "The Cobot processes a Component when the configured process is incompatible",
    (P.assembly.under_processing & (~P.assembly.is_valid)).eventually(),
)

__register_uca(
    "UCA10-P-3",
    "The Cobot starts the processing when no Component is currently held",
    ((P.cobot.position.in_tool) & P.tool.starts & ~P.cobot.has_assembly).eventually(),
)

__register_uca(
    "UCA10-P-4",
    "The Cobot processes a Component when minimum separation requirements are not met",
    (
        P.assembly.under_processing
        & (P.tool.distance.lt(P.constraints.tool.distance.operation, __TOLERANCE))
    ).eventually(),
)

__register_uca(
    "UCA10-P-5",
    "The Cobot processes a Component when personnel is present in the processing area",
    (
        P.assembly.under_processing
        & (P.operator.position.in_workspace | P.operator.position.in_tool)
    ).eventually(),
)

__register_uca(
    "UCA10-P-6", "The Cobot processes a Component when the tool is busy", BOT
)

__register_uca(
    "UCA10-P-7",
    "The Cobot processes a Component when the tool is under maintenance",
    BOT,
)

__register_uca(
    "UCA10-P-8", "The Cobot processes a Component while under maintenance", BOT
)

__register_uca(
    "UCA10-P-9",
    "The Cobot processes a Component held in the wrong position or orientation",
    (
        P.assembly.under_processing & ~P.assembly.is_orientation_valid
    ).eventually(),  # TODO Test
)

__register_uca(
    "UCA10-T-1",
    "The Cobot processes a component before it has been configured",
    P.assembly.under_processing & ~P.controller.is_configured,
)

__register_uca(
    "UCA10-T-2",
    "The Cobot processes a component after an incident occurred and before resolution",
    BOT,
)

__register_uca(
    "UCA10-T-3",
    "The Cobot processes a component before it has reached the required position and velocity",
    (
        P.assembly.under_processing
        & (P.cobot.velocity.gt(P.constraints.cobot.velocity.in_tool, __TOLERANCE))
    ).eventually(),
)

__register_uca(
    "UCA10-T-4",
    "The Cobot processes a component before the Component been secured",
    (P.assembly.under_processing & ~P.assembly.is_secured).eventually(),
)

__register_uca(
    "UCA11-N-1",
    "The Operator does not configure the process before operation",
    ~((~P.cobot.acts).until(P.controller.is_configured) | (~P.cobot.acts).always()),
)

__register_uca(
    "UCA11-P-1",
    "The operator configures the process when it is already configured",
    BOT,
)

__register_uca(
    "UCA11-T-1",
    "The Operator configures the process while a part is under processing",
    (P.controller.gets_configured & P.assembly.is_processed).eventually(),  # TODO Test
)

__register_uca(
    "UCA12-D-1",
    "The Operator does not complete the maintenance operation or return to the operating mode",
    BOT,
)

__register_uca(
    "UCA12-N-1",
    "The Operator does not perform maintenance when the Cobot signals an incident",
    BOT,
)

__register_uca(
    "UCA12-N-2", "The Operator does not perform regular maintenance of the Cobot", BOT
)

__register_uca(
    "UCA12-P-1",
    "The Operator performs maintenance while the Cobot is processing a part",
    BOT,
)

__register_uca(
    "UCA12-P-2",
    "The Operator performs maintenance while the Cobot is not set in the appropriate mode",
    BOT,
)

unsafe_control_actions = sorted(
    unsafe_control_actions, key=lambda u: (u.uid.split("-"))
)

uca_monitor = Monitor()
for uca in unsafe_control_actions:
    uca_monitor += uca.condition


def __register_hazard(uid, description, condition):
    """Register a new hazard"""
    return Hazard(uid, condition, description)


hazards = {
    __register_hazard(
        "1.1",
        "Violation of minimum separation requirements [Two entities hold onto the same assembly])",
        # Two manipulators hold on the assembly
        (
            (
                P.cobot.has_assembly
                & P.tool.has_assembly
                & P.cobot.is_moving
                & P.cobot.velocity.gt(7.5)
            )
            | (
                P.operator.has_assembly
                & P.cobot.has_assembly
                & (
                    (P.cobot.is_moving & P.cobot.velocity.gt(7.5))
                    | P.operator.is_moving
                )
            )
        ).eventually(),
    ),
    __register_hazard(
        "1.2",
        "Violation of minimum separation requirements [Cobot exceeds velocity constraints])",
        # Cobot moving faster than authorised at specific locations
        (
            reduce(
                operator.__or__,
                (
                    (
                        P.cobot.velocity.gt(
                            getattr(P.constraints.cobot.velocity, i), __TOLERANCE
                        )
                    )
                    & (getattr(P.cobot.position, i))
                    for i in ["in_bench", "in_workspace", "in_tool"]
                ),
                BOT,
            )
        ).eventually(),
    ),
    __register_hazard(
        "1.3",
        "Violation of minimum separation requirements "
        "[Cobot exceeds proximity velocity constraints])",
        (
            (P.cobot.velocity.gt(P.constraints.cobot.velocity.proximity, __TOLERANCE))
            & (P.cobot.distance.lt(P.constraints.cobot.distance.proximity, __TOLERANCE))
        ).eventually()
        # TODO Requires more proximity alert ranges?
        # TODO Add moving towards obstruction
        ,
    ),
    __register_hazard(
        "2",
        "Individual or Object in dangerous area [Temp: Obstruction with active Tool]",
        ~(
            (
                P.tool.is_running
                & (
                    P.tool.distance.lt(
                        P.constraints.tool.distance.operation, __TOLERANCE
                    )
                )
            )
            .implies(
                (
                    ~(
                        P.tool.is_running
                        & P.tool.distance.lt(
                            P.constraints.tool.distance.operation, __TOLERANCE
                        )
                    )
                ).eventually(lo=0.0, hi=1.0)
                | P.tool.is_running.always()
            )
            .always()
        ),
    ),
    __register_hazard(
        "3",
        "Equipment or Component subject to unnecessary stress",
        (reduce(operator.__or__, (d.is_damaged for d in Entities), BOT)).eventually(),
    ),
    __register_hazard(
        "4",
        "Supplied component cannot be correctly processed",
        # TODO Only check if picked up/used by cobot?
        P.assembly.under_processing
        & (
            P.assembly.is_damaged
            | ~P.assembly.is_valid
            | ~P.assembly.is_orientation_valid
        ),
    ),
    __register_hazard(
        "5",
        "Equipment operated outside safe conditions [Temp: Tool running without assembly]",
        (
            P.tool.is_running & ~(P.cobot.has_assembly & P.cobot.position.in_tool)
        ).eventually(),
    ),
    __register_hazard(
        "6",
        "Components not secured during processing or transport",
        (
            (~P.assembly.is_secured)
            & (P.assembly.under_processing | P.assembly.is_moving)
        ).eventually(),
    ),
    __register_hazard(
        "7",
        "Components do not move through the processing chain",
        ~(
            P.assembly.is_processed
            & P.assembly.position.in_bench
            & (~P.assembly.is_held)
        ).eventually(),
    ),
}

hazards = sorted(hazards, key=lambda h: h.uid)

hazard_monitor = Monitor(frozenset(h.condition for h in hazards))
