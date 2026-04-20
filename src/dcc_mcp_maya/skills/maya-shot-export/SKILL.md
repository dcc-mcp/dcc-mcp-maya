---
name: maya-shot-export
description: Maya shot export — export shots, frame ranges, cameras, and FBX/Alembic sequences for production pipelines
dcc: maya
version: 1.0.0
tags:
- maya
- export
- shot
- pipeline
- production
search-hint: shot, export, sequence, frame range, publish
license: MIT
allowed-tools:
- Bash
- Read
depends: []
tools:
- name: export_camera
  read_only_hint: true
  idempotent_hint: true
- name: export_shot_alembic
  read_only_hint: true
  idempotent_hint: true
- name: export_shot_fbx
  read_only_hint: true
  idempotent_hint: true
- name: get_shot_info
  read_only_hint: true
  idempotent_hint: true
---
# maya-shot-export

Shot-level export utilities for Maya production pipelines. Exports frame ranges,
cameras, and geometry sequences in FBX or Alembic format with shot metadata.

## Scripts

- `export_shot_fbx` — Export selected geometry within a frame range to FBX
- `export_shot_alembic` — Export selected objects as Alembic (.abc) sequence
- `export_camera` — Export a shot camera to FBX or Maya ASCII
- `get_shot_info` — Query current shot metadata (frame range, camera, scene name)
