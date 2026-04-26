---
name: maya-sets
description: Maya object set management — create sets, add and remove members, and query set contents. Use when grouping objects for render, deformation, or organization. Not for display layers or hierarchical grouping — use maya-display or maya-scene for that.
license: MIT
allowed-tools: Bash Read
metadata:
  dcc-mcp:
    dcc: maya
    layer: domain
    version: 1.0.0
    tags:
    - maya
    - set
    - collection
    - utility
    search-hint: group objects, object set, render set, deformer set, partition
    depends: []
    tools: tools.yaml
    groups: groups.yaml
---
> **Deprecated (merge bucket):** This skill contains only thin \maya.cmds\ wrappers.
> Use \xecute_python\ with \maya-scripting/references/RECIPES.md#sets\ instead.
> Will be removed in the next release.

# maya-sets

Maya sets skill. Provides actions for creating, managing, and listing Maya object sets.

## Scripts

- `create_set` — Create a Maya object set
- `add_to_set` — Add objects to an existing Maya object set
- `remove_from_set` — Remove objects from an existing Maya object set
- `list_sets` — List all Maya object sets in the scene
