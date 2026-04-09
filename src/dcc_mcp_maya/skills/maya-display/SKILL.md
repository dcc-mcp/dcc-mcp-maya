---
name: maya-display
description: "Maya display layers and viewport shading mode management"
dcc: maya
version: "1.0.0"
tags: [maya, display, layer, visibility]
license: "MIT"
allowed-tools: ["Bash", "Read"]
depends: []
---

# maya-display

Maya display skill. Provides actions for creating, setting, deleting, and listing display layers in Maya.

## Scripts

- `create_display_layer` — Create a display layer and optionally add objects to it
- `set_display_layer` — Assign an object to an existing display layer
- `delete_display_layer` — Delete a display layer
- `list_display_layers` — List all display layers in the scene
