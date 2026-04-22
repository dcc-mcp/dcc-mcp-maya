---
name: maya-constraints
description: Maya constraints — parent, point, orient, scale, aim and weighted constraints
license: MIT
allowed-tools: Bash Read
metadata:
  dcc-mcp:
    dcc: maya
    version: 1.0.0
    tags:
    - maya
    - constraint
    - rigging
    - parent
    - orient
    - aim
    search-hint: constraint, parent, orient, aim, point, scale
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
