---
name: maya-animation
description: "Maya animation keyframes, timeline, curves and simulation baking"
dcc: maya
version: "1.0.0"
tags: [maya, animation, keyframe, timeline]
license: "MIT"
allowed-tools: ["Bash", "Read"]
depends: []
tools:
  - name: set_keyframe
    description: "Set a keyframe on an object at the given time"
    source_file: scripts/set_keyframe.py
    read_only: false
    destructive: false
    idempotent: false
  - name: get_keyframes
    description: "Get all keyframe times for an object / attribute"
    source_file: scripts/get_keyframes.py
    read_only: true
    destructive: false
    idempotent: true
  - name: set_timeline
    description: "Set the playback and animation timeline range"
    source_file: scripts/set_timeline.py
    read_only: false
    destructive: false
    idempotent: true
  - name: get_current_time
    description: "Get the current frame number"
    source_file: scripts/get_current_time.py
    read_only: true
    destructive: false
    idempotent: true
  - name: set_current_time
    description: "Set the current frame number"
    source_file: scripts/set_current_time.py
    read_only: false
    destructive: false
    idempotent: true
  - name: delete_keyframes
    description: "Delete keyframes from an object within an optional frame range"
    source_file: scripts/delete_keyframes.py
    read_only: false
    destructive: true
    idempotent: false
  - name: bake_simulation
    description: "Bake simulation / constraints to keyframes on objects"
    source_file: scripts/bake_simulation.py
    read_only: false
    destructive: false
    idempotent: false
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
