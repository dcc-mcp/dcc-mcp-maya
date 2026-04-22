---
name: maya-constraints-advanced
description: Advanced Maya constraints — pole vector, IK handle constraints, space switching, and weighted constraint networks. Use when building complex rigging constraint setups. Not for basic single constraints or non-rigging tasks — use maya-constraints or maya-rig-utils for that.
license: MIT
allowed-tools: Bash Read
metadata:
  dcc-mcp:
    dcc: maya
    layer: domain
    version: 1.0.0
    tags:
    - maya
    - constraint
    - rigging
    - ik
    - space-switch
    search-hint: advanced rig constraint, space switch, pole vector, IK handle
    depends: []
    tools: tools.yaml
    groups: groups.yaml
---
# maya-constraints-advanced

Advanced Maya constraints skill. Provides actions for pole-vector constraints,
IK handle constraints, space-switching setups, and baking constrained animation.

## Scripts

- `add_pole_vector_constraint` — Add a pole vector constraint to an IK handle
- `bake_constraint` — Bake constrained animation to keyframes and remove constraints
- `get_constraint_weights` — Query the weights of all drivers on a constraint
- `set_constraint_weight` — Set the weight of a specific driver on a constraint
