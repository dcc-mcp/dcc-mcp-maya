---
name: maya-selection
description: Maya selection utilities — filter by type, grow, shrink, invert, and convert selections. Use when controlling which objects or components are active. Not for scene hierarchy queries or display visibility — use maya-scene or maya-display for that.
license: MIT
allowed-tools: Bash Read
metadata:
  dcc-mcp:
    dcc: maya
    layer: domain
    version: 1.0.0
    tags:
    - maya
    - selection
    - filter
    - component
    search-hint: filter selection, select by type, component selection, invert selection
    depends: []
    tools: tools.yaml
    groups: groups.yaml
---
> **Deprecated (merge bucket):** This skill contains only thin \maya.cmds\ wrappers.
> Use \xecute_python\ with \maya-scripting/references/RECIPES.md#selection\ instead.
> Will be removed in the next release.

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
