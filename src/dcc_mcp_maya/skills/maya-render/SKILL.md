---
name: maya-render
description: |-
  Pipeline stage — render globals and viewport capture: configure render
  settings, query them, capture playblasts. Use for producing final or
  preview imagery. Not for modeling (maya-mesh-ops), animation editing
  (maya-animation), or render farm submission (maya-render-farm).
license: MIT
allowed-tools: Bash Read
metadata:
  dcc-mcp:
    dcc: maya
    layer: domain
    stage: pipeline
    version: 1.1.0
    tags:
    - maya
    - render
    - playblast
    - settings
    - viewport
    search-hint: |-
      final output, preview render, playblast, viewport capture, render globals,
      set render settings, image format, frame range render
    aliases:
    - maya-render-settings
    side-effects:
    - reads-scene
    - writes-scene
    - writes-disk
    depends: []
    tools: tools.yaml
    groups: groups.yaml
---
# maya-render (Pipeline stage)

Render globals + viewport capture. Three small scripts that handle
"set render settings → playblast / read settings" without going to a
render farm. For distributed rendering, see `maya-render-farm`.

## Scripts

- `set_render_settings` — Set render parameters (resolution, frame range, renderer, image format)
- `get_render_settings` — Query current render settings
- `playblast` — Capture a viewport screenshot as a base64-encoded PNG
