---
name: maya-render
description: |-
  Pipeline stage — render globals, final-frame rendering, and viewport capture:
  configure render settings, query them, render frames, capture playblasts.
  Use for producing final or preview imagery. Not for modeling (maya-mesh-ops), animation editing
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
- `render_frame` — Render a single frame to disk without using model panels or playblast
- `capture_playblast_sequence` — Capture a playblast image sequence to disk
- `get_viewport_camera` — Query the active model panel camera

## Examples

Render one frame from the default renderable camera and return a base64 preview:

```json
{"tool": "maya_render__render_frame", "arguments": {"frame": 1, "width": 1280, "height": 720}}
```

Render through a named camera to a deterministic output prefix:

```json
{"tool": "maya_render__render_frame", "arguments": {"camera": "shotCam", "output_dir": "C:/renders/shot01", "output_name": "shot01_beauty", "return_base64": false}}
```
