---
name: maya-render-passes
description: Maya render passes — create, list, and configure render pass/AOV elements for multi-pass compositing
dcc: maya
version: 1.0.0
tags:
- maya
- render
- passes
- aov
- compositing
search-hint: render pass, aov, beauty, diffuse, specular
license: MIT
allowed-tools:
- Bash
- Read
depends: []
tools:
- name: create_render_pass
- name: enable_render_pass
  idempotent_hint: true
- name: list_render_passes
  read_only_hint: true
  idempotent_hint: true
- name: set_render_pass_output
  idempotent_hint: true
groups:
- name: rendering
  description: Render settings, layers, passes, and output tools
  default_active: false
  tools:
  - create_render_pass
  - enable_render_pass
  - list_render_passes
  - set_render_pass_output
---
# maya-render-passes

Render pass (render element / AOV) management for Maya. Works with Maya Software and
Arnold renderer render elements, enabling multi-pass compositing workflows.

## Scripts

- `create_render_pass` — Create a render pass element (beauty, diffuse, specular, shadow, etc.)
- `list_render_passes` — List all render pass elements in the current render layer
- `enable_render_pass` — Enable or disable a specific render pass element
- `set_render_pass_output` — Configure output path and image format for a render pass
