---
name: maya-camera-sequence
description: Maya camera sequencer — create, list, trim, and bake camera cuts for multi-shot sequences
dcc: maya
version: 1.0.0
tags:
- maya
- camera
- sequencer
- shots
- animation
search-hint: camera, sequence, film, multi-camera
license: MIT
allowed-tools:
- Bash
- Read
depends: []
tools:
- name: create_shot
- name: delete_shot
  destructive_hint: true
  idempotent_hint: true
- name: list_shots
  read_only_hint: true
  idempotent_hint: true
- name: set_shot_range
  idempotent_hint: true
groups:
- name: animation
  description: Animation, constraints, and motion capture tools
  default_active: false
  tools:
  - create_shot
  - delete_shot
  - list_shots
  - set_shot_range
---
# maya-camera-sequence

Camera Sequencer utilities for Maya. Manage multi-shot camera sequences using Maya's
built-in sequencer or shot nodes.

## Scripts

- `create_shot` — Create a Maya shot node and assign a camera for a frame range
- `list_shots` — List all shot nodes with their camera, start/end frame, and sequence order
- `set_shot_range` — Modify the start/end frame of an existing shot node
- `delete_shot` — Delete a shot node
