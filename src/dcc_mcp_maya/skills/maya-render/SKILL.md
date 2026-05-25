---
name: maya-render
description: |-
  Pipeline stage — render globals and viewport capture: configure render
  settings, query them, capture playblasts. Use for producing final or
  preview imagery. Not for modeling (maya-mesh-ops), animation editing
  (maya-animation), generic file import/export (maya-geometry), or render
  farm submission (maya-render-farm).
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
    - camera
    - capture
    - settings
    - viewport
    search-hint: |-
      final output, preview render, playblast, viewport capture, render globals,
      set render settings, image format, frame range render
    tools: tools.yaml
    groups: groups.yaml
---
# maya-render (Pipeline stage)

Render globals + viewport capture. This skill intentionally exposes only
renderer configuration, diagnostics, and render/viewport outputs. Generic
scene or geometry file import/export belongs to `maya-geometry`; shot
packaging belongs to `maya-shot-export`. For distributed rendering, see
`maya-render-farm`.

## Scripts

- `set_render_settings` — Set render parameters (resolution, frame range, renderer, image format)
- `get_render_settings` — Query current render settings
- `get_scene_render_stats` — Query render-facing scene statistics
- `set_render_quality` — Set render quality presets
- `capture_viewport` — Capture the active viewport as a base64-encoded PNG
- `playblast` — Capture a single viewport frame as a base64-encoded PNG
- `capture_playblast_sequence` — Capture a playblast image sequence to disk
- `get_viewport_camera` — Query the active model panel camera
