---
name: maya-display
description: Maya display layers and viewport shading mode management
license: MIT
allowed-tools: Bash Read
metadata:
  dcc-mcp:
    dcc: maya
    version: 1.0.0
    tags:
    - maya
    - display
    - layer
    - visibility
    search-hint: display, visibility, show, hide, wireframe, layer
    depends: []
    tools: tools.yaml
    groups: groups.yaml
---
# maya-display

Maya display skill. Provides actions for creating, setting, deleting, and listing display layers in Maya.

## Scripts

- `create_display_layer` — Create a display layer and optionally add objects to it
- `set_display_layer` — Assign an object to an existing display layer
- `delete_display_layer` — Delete a display layer
- `list_display_layers` — List all display layers in the scene
