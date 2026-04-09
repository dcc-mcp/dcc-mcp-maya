---
name: maya-render-layers
description: "Maya render layers — create, assign, list and manage render layer overrides"
dcc: maya
version: "1.0.0"
tags: [maya, render, layer, renderlayer]
license: "MIT"
allowed-tools: ["Bash", "Read"]
depends: []
---

# maya-render-layers

Maya render layers skill. Provides actions for creating, assigning, listing, deleting render layers and setting render layer attribute overrides.

## Scripts

- `create_render_layer` — Create a render layer and optionally add objects to it
- `set_render_layer` — Assign an object to an existing render layer
- `list_render_layers` — List all render layers in the scene
- `delete_render_layer` — Delete a render layer from the scene
- `set_render_layer_attribute` — Set an attribute override on a render layer node
