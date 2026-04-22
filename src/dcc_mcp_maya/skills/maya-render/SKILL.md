---
name: maya-render
description: Maya render settings and viewport capture — configure render globals, playblast, and viewport snapshots. Use when producing final or preview images. Not for modeling, animation editing, or render farm submission — use maya-mesh-ops, maya-animation, or maya-render-farm for that.
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
    - playblast
    - settings
    search-hint: final output, preview render, playblast, viewport capture
    depends: []
    tools: tools.yaml
    groups: groups.yaml
---
# maya-render

Maya render skill. Provides actions for managing render settings and capturing
viewport images.

## Scripts

- `set_render_settings` — Set render parameters (resolution, frame range, renderer, image format)
- `get_render_settings` — Query current render settings
- `playblast` — Capture a viewport screenshot as a base64-encoded PNG
