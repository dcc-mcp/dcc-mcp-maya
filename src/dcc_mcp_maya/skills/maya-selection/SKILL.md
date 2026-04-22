---
name: maya-selection
description: Maya selection utilities — filter, grow, shrink, invert, and convert
  selections
license: MIT
allowed-tools: Bash Read
metadata:
  dcc-mcp:
    dcc: maya
    version: 1.0.0
    tags:
    - maya
    - selection
    - filter
    - component
    search-hint: select, filter, type, hierarchy, component
    depends: []
    tools: tools.yaml
    groups: groups.yaml
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
