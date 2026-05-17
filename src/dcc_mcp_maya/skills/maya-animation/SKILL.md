---
name: maya-animation
description: |-
  Authoring stage — keyframes, timeline, animation curves, constraint
  baking, and curve I/O. Use whenever you create or edit time-based motion.
  Not for rigging setup (maya-rigging), pose library (maya-pose-library),
  or render output (maya-render).
license: MIT
allowed-tools: Bash Read
metadata:
  dcc-mcp:
    dcc: maya
    layer: domain
    stage: authoring
    version: 1.1.0
    tags:
    - maya
    - animation
    - keyframe
    - timeline
    - curve
    - bake
    search-hint: |-
      animate motion, keyframe, set key, timeline range, animation curve,
      curve tangent, bake constraint, bake simulation, anim file import export
    depends: []
    tools: tools.yaml
    groups: groups.yaml
---
# maya-animation (Authoring stage)

Keyframes, timeline, curves, constraint / simulation baking, and
animation curve I/O. Fourteen scripts in three logical clusters:

1. **Frame / time queries** — `get_current_time`, `set_current_time`,
   `set_timeline`, `get_frame_range`, `query_scene_time_info`.
2. **Key editing** — `set_keyframe`, `get_keyframes`, `delete_keyframes`,
   `list_animation_curves`, `set_animation_curve_tangent`.
3. **Bake + persistence** — `bake_simulation`, `bake_constraints`,
   `export_animation_curves`, `import_animation_curves`.

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
- `get_frame_range` — Return the scene's animation frame range
