---
name: maya-display
description: |-
  Scene stage — Maya display layers and viewport visibility management. Use
  for organising what artists / agents see in the viewport (display layers,
  show/hide). Not for render layers or final imagery — use maya-render or a
  future maya-render-layers skill for that.
license: MIT
allowed-tools: Bash Read
metadata:
  dcc-mcp:
    dcc: maya
    layer: domain
    stage: scene
    version: 1.1.0
    tags:
    - maya
    - display
    - layer
    - visibility
    search-hint: |-
      viewport visibility, display layer, show hide, layer assign,
      hide group, isolate selection
    tools: tools.yaml
    groups: groups.yaml
---
# maya-display (Scene stage)

Display layers and viewport visibility. Strictly **viewport-side**: nothing
here changes geometry, materials, or render output.

## Scripts

- `create_display_layer` — Create a display layer and optionally add objects to it
- `set_display_layer` — Assign an object to an existing display layer
- `delete_display_layer` — Delete a display layer
- `list_display_layers` — List all display layers in the scene
