from csi.monitor import P
from mtl import BOT


manipulators = [P.cobot, P.operator]


damageable = [P.cobot, P.operator, P.assembly, P.tool]


# FIXME Extend to any non-expected entity
P.workspace.has_obstruction = P.operator.position.in_workspace


# Assembly is held by a manipulator
P.assembly.is_held = BOT
for r in manipulators:
    P.assembly.is_held = P.assembly.is_held | r.has_assembly


# FIXME COBOT/OPERATOR is_moving predicate uses mtl Next operator adds time (t-dt) in the trace, where dt is eval param
# Capture an entity getting damaged
for r in damageable:
    r.suffers_damage = (~r.is_damaged) & (r.is_damaged >> 1)


P.operator.grabs_assembly = (~P.operator.has_assembly) & (P.operator.has_assembly >> 1)


P.operator.releases_assembly = P.operator.has_assembly & (~P.operator.has_assembly >> 1)


P.controller.gets_configured = (~P.controller.is_configured) & (
    P.controller.is_configured >> 1
)


P.tool.starts = (~P.tool.is_running) & (P.tool.is_running >> 1)


# Assembly gets delivered after processing
P.assembly.is_delivered = P.assembly.is_processed.implies(
    (P.cobot.position.in_bench & (~P.cobot.has_assembly)).eventually()
).always()


P.assembly.needs_secured = P.cobot.has_assembly & (~P.cobot.position.in_bench)


P.cobot.grabs_assembly = (~P.cobot.has_assembly) & (P.cobot.has_assembly >> 1)


P.cobot.releases_assembly = P.cobot.has_assembly & ((~P.cobot.has_assembly) >> 1)


P.cobot.acts = P.cobot.grabs_assembly | P.cobot.releases_assembly | P.cobot.is_moving
