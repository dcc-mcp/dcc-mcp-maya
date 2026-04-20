---
name: maya-animation
description: Maya animation keyframes, timeline, curves and simulation baking
dcc: maya
version: 1.0.0
tags:
- maya
- animation
- keyframe
- timeline
search-hint: keyframe, timeline, animate, curves, bake, simulation, constraint, tangent
license: MIT
allowed-tools:
- Bash
- Read
depends: []
tools:
- name: bake_constraints
- name: bake_simulation
  description: Bake simulation / constraints to keyframes on objects
- name: delete_keyframes
  description: Delete keyframes from an object within an optional frame range
  destructive_hint: true
  idempotent_hint: true
- name: export_animation_curves
  read_only_hint: true
  idempotent_hint: true
- name: get_current_time
  description: Get the current frame number
  read_only_hint: true
  idempotent_hint: true
- name: get_frame_range
  read_only_hint: true
  idempotent_hint: true
- name: get_keyframes
  description: Get all keyframe times for an object / attribute
  read_only_hint: true
  idempotent_hint: true
- name: import_animation_curves
- name: list_animation_curves
  read_only_hint: true
  idempotent_hint: true
- name: query_scene_time_info
  read_only_hint: true
  idempotent_hint: true
- name: set_animation_curve_tangent
  idempotent_hint: true
- name: set_current_time
  description: Set the current frame number
  idempotent_hint: true
- name: set_keyframe
  description: Set a keyframe on an object at the given time
  idempotent_hint: true
- name: set_timeline
  description: Set the playback and animation timeline range
  idempotent_hint: true
groups:
- name: animation
  description: Animation, constraints, and motion capture tools
  default_active: false
  tools:
  - bake_constraints
  - bake_simulation
  - delete_keyframes
  - export_animation_curves
  - get_current_time
  - get_frame_range
  - get_keyframes
  - import_animation_curves
  - list_animation_curves
  - query_scene_time_info
  - set_animation_curve_tangent
  - set_current_time
  - set_keyframe
  - set_timeline
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
