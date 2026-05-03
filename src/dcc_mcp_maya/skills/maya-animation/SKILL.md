---
name: maya-animation
description: Maya animation keyframes, timeline, curves, constraint baking, and simulation caching. Use when creating or editing time-based motion. Not for rigging setup or render output — use maya-rigging or maya-render for that.
license: MIT
allowed-tools: Bash Read
metadata:
  dcc-mcp:
    dcc: maya
    layer: domain
    version: 1.0.0
    tags:
    - maya
    - animation
    - keyframe
    - timeline
    search-hint: animate motion, keyframe, timeline, curve editing, bake simulation
      tangent
    depends: []
    tools: tools.yaml
    groups: groups.yaml
---
# maya-animation

Maya animation skill. Provides actions for managing keyframes, timeline settings, animation curves, baking simulations and constraints, and importing/exporting animation data.

## Scripts

- `set_keyframe` — Set a keyframe on an object at the given time
- `get_keyframes` — Get all keyframe times for an object / attribute
- `set_timeline` — Set the playback and animation timeline range
- `get_current_time` — Get the current frame number
- `set_current_time` — Set the current frame number
- `delete_keyframes` — Delete keyframes from an object within an optional frame range
- `bake_simulation` — Bake simulation / constraints to keyframes on objects
- `list_animation_curves` — List all animCurve nodes driving an object
- `set_animation_curve_tangent` — Set the tangent type on one or all keyframes of an animation curve
- `bake_constraints` — Bake constraint-driven animation to explicit keyframes
- `export_animation_curves` — Export animation curves for an object to a Maya .anim file
- `import_animation_curves` — Import animation curves from a file and optionally apply them to an object
- `query_scene_time_info` — Query the current scene time and playback settings
