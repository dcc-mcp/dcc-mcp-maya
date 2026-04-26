---
name: maya-utility
description: Maya utility nodes and scene statistics — freeze transforms, center pivot, and convert units. Use when performing general scene cleanup and normalization. Not for modeling, animation, or rendering — use maya-mesh-ops, maya-animation, or maya-render for that.
license: MIT
allowed-tools: Bash Read
metadata:
  dcc-mcp:
    dcc: maya
    layer: domain
    version: 1.0.0
    tags:
    - maya
    - utility
    - node
    - scene
    search-hint: scene cleanup, freeze transform, center pivot, normalize units
    depends: []
    tools: tools.yaml
---
> **Deprecated (merge bucket):** This skill contains only thin \maya.cmds\ wrappers.
> Use \xecute_python\ with \maya-scripting/references/RECIPES.md#utility\ instead.
> Will be removed in the next release.

# maya-utility

Maya utility skill. Provides actions for creating utility/shading nodes and querying scene statistics.

## Scripts

- `create_utility_node` — Create any Maya utility or shading node by type
- `get_scene_statistics` — Query scene-level statistics: polygon counts, node counts and memory
