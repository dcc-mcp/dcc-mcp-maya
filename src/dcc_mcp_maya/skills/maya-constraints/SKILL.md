---
name: maya-constraints
description: Maya constraints — parent, point, orient, scale, and aim constraints with weights. Use when establishing spatial relationships between objects. Not for advanced space switching or IK handles — use maya-constraints-advanced or maya-rigging for that.
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
    - parent
    - orient
    - aim
    search-hint: spatial relationship, parent constraint, aim constraint, follow
    depends: []
    tools: tools.yaml
    groups: groups.yaml
---
# maya-constraints

Maya constraints skill. Provides actions for adding, removing, listing, and
creating weighted constraints on Maya objects.

## Scripts

- `add_constraint` — Add a Maya constraint from source to target
- `remove_constraint` — Remove constraint(s) from a target object
- `list_constraints` — List all constraints applied to a target object
- `create_constraint_weighted` — Create a weighted multi-source constraint
