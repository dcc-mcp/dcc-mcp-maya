---
name: maya-render
description: Maya render settings and viewport capture
dcc: maya
version: 1.0.0
tags:
- maya
- render
- playblast
- settings
search-hint: render, settings, playblast, capture, viewport
license: MIT
allowed-tools:
- Bash
- Read
depends: []
tools:
- name: capture_viewport
- name: export_selection
  read_only_hint: true
  idempotent_hint: true
- name: get_render_settings
  description: Query current render settings
  read_only_hint: true
  idempotent_hint: true
- name: get_scene_render_stats
  read_only_hint: true
  idempotent_hint: true
- name: import_file
- name: playblast
  description: Capture a viewport screenshot as a base64-encoded PNG
- name: set_render_quality
  idempotent_hint: true
- name: set_render_settings
  description: Set render parameters (resolution, frame range, renderer, image format)
  idempotent_hint: true
groups:
- name: rendering
  description: Render settings, layers, passes, and output tools
  default_active: false
  tools:
  - capture_viewport
  - export_selection
  - get_render_settings
  - get_scene_render_stats
  - import_file
  - playblast
  - set_render_quality
  - set_render_settings
---
# maya-render

Maya render skill. Provides actions for managing render settings and capturing
viewport images.

## Scripts

- `set_render_settings` — Set render parameters (resolution, frame range, renderer, image format)
- `get_render_settings` — Query current render settings
- `playblast` — Capture a viewport screenshot as a base64-encoded PNG
