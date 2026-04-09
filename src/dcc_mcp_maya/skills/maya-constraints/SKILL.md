---
name: maya-constraints
description: "Maya constraints — parent, point, orient, scale, aim and weighted constraints"
dcc: maya
version: "1.0.0"
tags: [maya, constraint, rigging]
license: "MIT"
allowed-tools: ["Bash", "Read"]
depends: []
---

# maya-constraints

Maya constraints skill. Provides actions for adding, removing, listing, and
creating weighted constraints on Maya objects.

## Scripts

- `add_constraint` — Add a Maya constraint from source to target
- `remove_constraint` — Remove constraint(s) from a target object
- `list_constraints` — List all constraints applied to a target object
- `create_constraint_weighted` — Create a weighted multi-source constraint
