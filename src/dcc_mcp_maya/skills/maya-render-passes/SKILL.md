---
name: maya-render-passes
description: Maya render passes — create, list, and configure render pass/AOV elements
  for multi-pass compositing
license: MIT
allowed-tools: Bash Read
metadata:
  dcc-mcp:
    dcc: maya
    version: 1.0.0
    tags:
    - maya
    - render
    - passes
    - aov
    - compositing
    search-hint: render pass, aov, beauty, diffuse, specular
    depends: []
    tools: tools.yaml
    groups: groups.yaml
---
# maya-render-passes

Render pass (render element / AOV) management for Maya. Works with Maya Software and
Arnold renderer render elements, enabling multi-pass compositing workflows.

## Scripts

- `create_render_pass` — Create a render pass element (beauty, diffuse, specular, shadow, etc.)
- `list_render_passes` — List all render pass elements in the current render layer
- `enable_render_pass` — Enable or disable a specific render pass element
- `set_render_pass_output` — Configure output path and image format for a render pass
