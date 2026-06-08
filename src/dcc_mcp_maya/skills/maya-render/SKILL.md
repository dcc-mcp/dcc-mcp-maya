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
    version: 1.2.0
    tags:
    - maya
    - render
    - playblast
    - camera
    - capture
    - settings
    - viewport
    - debug
    - snapshot
    search-hint: |-
      final output, preview render, playblast, viewport capture, render globals,
      set render settings, image format, frame range render, debug snapshot,
      MP4 preview, render intent, VP2 fallback
    tools: tools.yaml
    groups: groups.yaml
    resources:
    - docs://maya-render
---
# maya-render (Pipeline stage)

Render globals + viewport capture. This skill intentionally exposes only
renderer configuration, diagnostics, and render/viewport outputs. Generic
scene or geometry file import/export belongs to `maya-geometry`; shot
packaging belongs to `maya-shot-export`. For distributed rendering, see
`maya-render-farm`.

## Render intents → tool routing

This skill covers three high-level user intents. Each maps to a primary tool
and one or more supporting tools:

| Intent | Primary tool | Supporting tools | When to use |
|--------|-------------|------------------|-------------|
| **Output a final rendered frame** (beauty pass, look-dev check) | `render_frame` | `set_render_settings`, `get_render_settings`, `set_render_quality` | Render from the active renderer (Arnold / Maya Software). Independent of viewport — works when Maya is minimized or in batch mode. |
| **Collect debug / diagnostic evidence** (scene inspection, bug report) | `debug_scene_snapshot` | `get_scene_render_stats`, `get_viewport_camera`, `render_frame` (internal) | Combines DAG summary, optional render preview, and optional Maya UI capture in one call. `render_frame` is called internally for preview when available. |
| **Record a viewport animation preview** (anim review, dailies, MP4 clip) | `playblast_to_mp4` | `capture_playblast_sequence`, `capture_viewport`, `playblast` | Viewport-based; requires a visible model panel for best results. Falls back to off-screen when Maya is minimized. Requires `ffmpeg` on PATH for MP4 encoding. |

> **Gateway users:** Read `resources/read uri=gateway://docs/agent-workflows` for
> platform-agnostic efficiency patterns (search → describe → call, instances,
> resource/list+read). The intent routing above is Maya-specific; the gateway doc
> holds general protocol guidance that applies across all DCCs.

## VP2 fallback flow

When viewport-based tools (`playblast`, `playblast_to_mp4`, `capture_viewport`)
fail or produce empty output — typically because Maya is minimized, running in
batch mode, or has no visible model panel — the **recommended fallback** is to
use `render_frame` for the same frame:


```
[User wants viewport preview]
        |
        v
playblast / playblast_to_mp4 / capture_viewport
        |
        +--- Success -> return image / MP4
        |
        +--- Failure (no model panel, minimized, batch, empty sequence)
                |
                v
        Render fallback:
        1. Set renderer to mayaSoftware via set_render_settings (fast, no plugin)
        2. Call render_frame(camera=..., frame=..., return_base64=true)
        3. Return preview image in context.image_base64
```

Concrete error patterns and their fallback:

| Error | Fallback |
|-------|----------|
| `cmds.playblast` fails with "no active model panel" | Use `render_frame` — it does not require a model panel. |
| Maya is in batch mode (`cmds.about(batch=True)`) | `render_frame` works natively; playblast tools auto-enable `offScreen` but still need a Maya window. |
| playblast produces 0-byte image files | Render the same frame via `render_frame`; if that also fails, check the renderer plugin (e.g. MtoA). |
| ffmpeg not found on PATH (for `playblast_to_mp4`) | Use `capture_playblast_sequence` to get image frames, or fall back to `render_frame` for single-frame preview. |

The common agent workflow for "get a picture when everything else fails":

```python
# Minimal fallback — no viewport needed, no ffmpeg needed
maya_render__set_render_settings(renderer="mayaSoftware")
result = maya_render__render_frame(camera="persp", frame=1, return_base64=True)
```

## Scripts

- `set_render_settings` — Set render parameters (resolution, frame range, renderer, image format)
- `get_render_settings` — Query current render settings
- `get_scene_render_stats` — Query render-facing scene statistics
- `set_render_quality` — Set render quality presets
- `capture_viewport` — Capture the active viewport as a base64-encoded PNG
- `playblast` — Capture a single viewport frame as a base64-encoded PNG
- `render_frame` — Render a single frame to disk using the active renderer (Arnold / Maya Software).
  Independent of model panels and playblast — works when Maya is minimized or in batch mode.
  Supports Arnold render via MEL invocations (`arnoldRender`) and Maya Software via `cmds.render`.
  Returns output path + optional base64 image payload in `context.image_base64`.
  See **VP2 fallback flow** above for error recovery patterns.
- `capture_playblast_sequence` — Capture a playblast image sequence to disk
- `playblast_to_mp4` — Capture a viewport animation preview and encode it to MP4 with ffmpeg.
  Requires a visible modelPanel and ffmpeg on PATH. Falls back to off-screen capture when Maya
  is minimized or running in batch mode. Returns the MP4 path, frame count, resolution, and
  viewport renderer metadata. Set `keep_frames=true` to retain the intermediate PNG sequence.
- `debug_scene_snapshot` — Collect scene structure plus optional render preview and UI screenshot.
  Internal flow: `_scene_summary()` walks the DAG for transform/mesh/camera/light counts and
  a sample of named nodes → optionally calls `render_frame` at reduced resolution (640x480)
  for a visual preview → optionally captures the Maya Qt window state via `_dev_session.capture_ui`.
  Result contains `scene_summary` (struct), `preview` (optional render result), and `ui_capture`
  (optional UI snapshot).
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

Capture an MP4 viewport preview:

```json
{"tool": "maya_render__playblast_to_mp4", "arguments": {"start_frame": 1, "end_frame": 48, "fps": 24, "width": 1280, "height": 720}}
```

Collect debug evidence for an agent:

```json
{"tool": "maya_render__debug_scene_snapshot", "arguments": {"max_nodes": 40, "preview_width": 640, "preview_height": 480, "include_ui": true}}
```

Use VP2 fallback when playblast is unavailable (Maya minimized or batch mode):

```json
[
  {"tool": "maya_render__set_render_settings", "arguments": {"renderer": "mayaSoftware"}},
  {"tool": "maya_render__render_frame", "arguments": {"camera": "persp", "frame": 1, "return_base64": true}}
]
```

## Cross-references

- [`../../SKILLS_INDEX.md`](../../SKILLS_INDEX.md) — Full skill taxonomy and task → skill chains.
  The `pipeline` stage row groups `maya-render` with `maya-dev`, `maya-pipeline`,
  `maya-shot-export`, and `maya-render-farm`.
- `gateway://docs/agent-workflows` — Platform-agnostic MCP efficiency guidance (search →
  describe → call, instances, resources). Maya-specific intent routing lives in this file.
- `maya-render-farm/SKILL.md` — Distributed / farm-based rendering (Deadline, etc.).
  Use when you need to submit frames to a render queue rather than rendering locally.
- `maya-shot-export/SKILL.md` — Shot packaging and publishing; wraps render outputs
  into a publishable package with metadata.
- `maya-geometry/SKILL.md` — FBX/OBJ import/export for scene interchange.
- `maya-scene/SKILL.md` — Scene file lifecycle, DAG navigation, and basic node query.
- `examples/workflows/maya_bulk_rbd_fbx.md` — End-to-end workflow example with
  FBX interchange.
