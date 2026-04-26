---
name: maya-attributes
description: Maya node attribute management — get, set, lock, unlock, and create custom attributes. Use when reading or writing node properties. Not for scene-level operations, node connections, or scripting — use maya-scene, maya-node-graph, or maya-scripting for that.
license: MIT
allowed-tools: Bash Read
metadata:
  dcc-mcp:
    dcc: maya
    layer: domain
    version: 1.0.0
    tags:
    - maya
    - attribute
    - node
    - utility
    search-hint: node property, custom attribute, get value, set attribute
    depends: []
    tools: tools.yaml
---
> **Deprecated (merge bucket):** This skill contains only thin \maya.cmds\ wrappers.
> Use \xecute_python\ with \maya-scripting/references/RECIPES.md#attributes\ instead.
> Will be removed in the next release.

# maya-attributes

Maya attributes skill. Provides actions for getting and setting attribute values,
and managing custom attributes on Maya nodes.

## Scripts

- `get_attribute` — Get the value of an attribute on a Maya node
- `set_attribute` — Set the value of an attribute on a Maya node
- `add_attribute` — Add a custom attribute to a Maya node
- `delete_attribute` — Delete a custom (user-defined) attribute from a Maya node
- `list_attributes` — List attributes on a Maya node
