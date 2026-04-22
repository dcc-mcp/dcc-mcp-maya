---
name: maya-render-layers
description: Maya render layers — create, assign objects, list, and manage render layer overrides. Use when splitting a scene into multi-pass render configurations. Not for render pass elements or final submission — use maya-render-passes or maya-render-farm for that.
license: MIT
allowed-tools: Bash Read
metadata:
  dcc-mcp:
    dcc: maya
    layer: domain
    version: 1.0.0
    tags:
    - maya
    - render
    - layer
    - renderlayer
    search-hint: multi-pass setup, render layer override, split passes
    depends: []
    tools: tools.yaml
    groups: groups.yaml
---
# maya-render-layers

Maya render layers skill. Provides actions for creating, assigning, listing, deleting render layers and setting render layer attribute overrides.

## Scripts

- `create_render_layer` — Create a render layer and optionally add objects to it
- `set_render_layer` — Assign an object to an existing render layer
- `list_render_layers` — List all render layers in the scene
- `delete_render_layer` — Delete a render layer from the scene
- `set_render_layer_attribute` — Set an attribute override on a render layer node
