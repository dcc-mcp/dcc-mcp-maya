---
name: maya-pose-library
description: Maya pose library — save, load, apply, and manage character poses as JSON snapshots
dcc: maya
version: 1.0.0
tags:
- maya
- animation
- pose
- library
- rigging
search-hint: pose, library, save pose, apply pose
license: MIT
allowed-tools:
- Bash
- Read
depends: []
tools:
- name: list_poses
  read_only_hint: true
  idempotent_hint: true
- name: load_pose
- name: mirror_pose
- name: save_pose
groups:
- name: animation
  description: Animation, constraints, and motion capture tools
  default_active: false
  tools:
  - list_poses
  - load_pose
  - mirror_pose
  - save_pose
---
# maya-pose-library

Pose capture and application utilities for Maya. Saves attribute snapshots to JSON
files and restores them, enabling pose library workflows for character animation.

## Scripts

- `save_pose` — Save current attribute values of selected controls to a JSON pose file
- `load_pose` — Apply a saved pose JSON file to matching controls in the scene
- `list_poses` — List all saved pose files in a directory
- `mirror_pose` — Mirror pose by applying left/right attribute swapping convention
