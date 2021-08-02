import itertools
import operator

from functools import reduce

from csi.safety.stpa import Hazard
from csi.monitor import Monitor
from ..monitor import Entities
from mtl import BOT

from ..monitor import P


__TOLERANCE = 5.0


def __register_hazard(uid, description, condition):
    """Register a new hazard"""
    return Hazard(uid, condition, description)


hazards = {
    __register_hazard(
        "1.1",
        "Violation of minimum separation requirements [Two entities hold onto the same assembly])",
        # Two manipulators hold on the assembly
        (
            reduce(
                operator.__or__,
                (
                    i.has_assembly & j.has_assembly & (i.is_moving | j.is_moving)
                    for i, j in itertools.combinations(Entities, 2)
                ),
                BOT,
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
        "Violation of minimum separation requirements [Cobot exceeds proximity velocity constraints])",
        # Cobot moving faster than authorised in close proximity
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
            .implies((~P.tool.is_running).eventually(lo=0.0, hi=0.05))
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
        "Supplied component cannot be correctly processed",  # TODO Only check if picked up/used by cobot?
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

hazard_monitor = Monitor({h.condition for h in hazards})
