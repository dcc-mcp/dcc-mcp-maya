---
name: maya-constraints-advanced
description: "Advanced Maya constraints — pole vector, IK handle constraints, space-switch baking and constraint blending"
dcc: maya
version: "1.0.0"
tags: [maya, constraint, rigging, ik, space-switch]
license: "MIT"
allowed-tools: ["Bash", "Read"]
depends: []
---

# maya-constraints-advanced

Advanced Maya constraints skill. Provides actions for pole-vector constraints,
IK handle constraints, space-switching setups, and baking constrained animation.

## Scripts

- `add_pole_vector_constraint` — Add a pole vector constraint to an IK handle
- `bake_constraint` — Bake constrained animation to keyframes and remove constraints
- `get_constraint_weights` — Query the weights of all drivers on a constraint
- `set_constraint_weight` — Set the weight of a specific driver on a constraint
