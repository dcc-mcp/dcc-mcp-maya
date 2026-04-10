---
name: maya-selection
description: "Maya selection utilities — filter, grow, shrink, invert, and convert selections"
dcc: maya
version: "1.0.0"
tags: [maya, selection, filter, component]
license: "MIT"
allowed-tools: ["Bash", "Read"]
depends: []
---

# maya-selection

Maya selection skill. Provides advanced selection utilities beyond basic object selection:
component-level selection, conversion between selection modes, growing/shrinking, inverting,
and filtering by criteria.

## Scripts

- `grow_selection` — Grow the current component selection by one shell ring
- `shrink_selection` — Shrink the current component selection by one shell ring
- `invert_selection` — Invert the current selection within its context
- `convert_selection` — Convert the current selection to a different component type
- `select_similar` — Select objects with similar topology or material
