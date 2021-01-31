import itertools
import operator

from functools import reduce

from .aliases import damageable, manipulators
from csi.safety.stpa import Hazard
from csi.monitor import Monitor, P
from mtl import BOT


hazards = {
    Hazard(
        1,
        "Violation of minimum separation requirements [Temp: Obstruction with moving Cobot])",
        # Two manipulators hold on the assembly
        (
            reduce(
                operator.__or__,
                (
                    i.has_assembly & j.has_assembly
                    for i, j in itertools.combinations(manipulators, 2)
                ),
                BOT,
            )
        ).eventually()
        |
        # Cobot moving faster than authorised at specific locations
        (
            reduce(
                operator.__or__,
                (
                    (
                        P.cobot.velocity
                        > getattr(P.constraints.cobot.velocity, i.lower())
                    )
                    & (P.cobot.position[i])
                    for i in ["in_bench", "in_workspace", "in_tool"]
                ),
                BOT,
            )
        ).eventually()
        |
        # Cobot moving faster than authorised in close proximity
        (
            (P.cobot.velocity > P.constraints.cobot.velocity.proximity)
            & (P.cobot.distance < P.constraints.cobot.distance.proximity)
        ).eventually()
        # TODO Requires more proximity alert ranges?
        # TODO Add moving towards obstruction
        ,
    ),
    Hazard(
        2,
        "Individual or Object in dangerous area [Temp: Obstruction with active Tool]",
        (
            P.tool.is_running
            & (P.tool.distance < P.constraints.tool.distance.operation)
        ).eventually(),
    ),
    Hazard(
        3,
        "Equipment or Component subject to unnecessary stress",
        (reduce(operator.__or__, (d.is_damaged for d in damageable), BOT)).eventually(),
    ),
    Hazard(
        4,
        "Supplied component cannot be correctly processed",  # TODO Only check if picked up/used by cobot?
        P.assembly.under_processing
        & (
            P.assembly.is_damaged
            | ~P.assembly.is_valid
            | ~P.assembly.is_orientation_valid
        ),
    ),
    Hazard(
        5,
        "Equipment operated outside safe conditions [Temp: Tool running without assembly]",
        (
            P.tool.is_running & ~(P.cobot.has_assembly & P.cobot.position.in_tool)
        ).eventually(),
    ),
    Hazard(
        6,
        "Components not secured during processing or transport",
        (
            (~P.assembly.is_secured)
            & (P.assembly.under_processing | P.assembly.is_moving)
        ).eventually(),
    ),
    Hazard(
        7,
        "Components do not move through the processing chain",
        ~(
            P.assembly.is_processed
            & P.assembly.position.in_bench
            & (~P.assembly.is_held)
        ).eventually(),
    ),
}

hazards = sorted(hazards, key=lambda h: h.uid)

hazard_monitor = Monitor({h.condition for h in hazards})
