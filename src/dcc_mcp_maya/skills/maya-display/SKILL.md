---
name: maya-display
description: Maya display layers and viewport shading mode management — create layers, toggle visibility, and set wireframe/shaded modes. Use when controlling visual feedback in the viewport. Not for render layer setup or final output — use maya-render-layers or maya-render for that.
license: MIT
allowed-tools: Bash Read
metadata:
  dcc-mcp:
    dcc: maya
    layer: domain
    version: 1.0.0
    tags:
    - maya
    - display
    - layer
    - visibility
    search-hint: viewport visibility, display layer, wireframe shaded, show hide
    depends: []
    tools: tools.yaml
    groups: groups.yaml
---
> **Deprecated (merge bucket):** This skill contains only thin \maya.cmds\ wrappers.
> Use \xecute_python\ with \maya-scripting/references/RECIPES.md#display\ instead.
> Will be removed in the next release.

# maya-display

Maya display skill. Provides actions for creating, setting, deleting, and listing display layers in Maya.

## Scripts

- `create_display_layer` — Create a display layer and optionally add objects to it
- `set_display_layer` — Assign an object to an existing display layer
- `delete_display_layer` — Delete a display layer
- `list_display_layers` — List all display layers in the scene
