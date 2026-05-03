---
name: maya-expressions
description: Maya expression nodes — create, list, and delete procedural expressions that drive attributes. Use when building procedural animation or rig logic. Not for keyframe animation or general scripting — use maya-animation or maya-scripting for that.
license: MIT
allowed-tools: Bash Read
metadata:
  dcc-mcp:
    dcc: maya
    layer: domain
    version: 1.0.0
    tags:
    - maya
    - expression
    - scripting
    - procedural
    search-hint: procedural animation, expression node, drive attribute
    depends: []
    tools: tools.yaml
    groups: groups.yaml
---
> **Deprecated (merge bucket):** This skill contains only thin \maya.cmds\ wrappers.
> Use \xecute_python\ with \maya-scripting/references/RECIPES.md#expressions\ instead.
> Will be removed in the next release.

# maya-expressions

Maya expressions skill. Provides actions for creating, listing, and deleting Maya expression nodes.

## Scripts

- `create_expression` — Create a Maya expression node
- `list_expressions` — List Maya expression nodes in the scene
- `delete_expression` — Delete a Maya expression node by name
