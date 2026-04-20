---
name: maya-toon
description: Maya toon shading — create toon outlines, fill shaders, and cel-shading looks using Maya's built-in toon system
dcc: maya
version: 1.0.0
tags:
- maya
- toon
- shading
- npr
- stylized
search-hint: toon, outline, cartoon, cel shading
license: MIT
allowed-tools:
- Bash
- Read
depends: []
tools:
- name: add_toon_outline
- name: create_toon_shader
- name: list_toon_outlines
  read_only_hint: true
  idempotent_hint: true
- name: set_outline_width
  idempotent_hint: true
groups:
- name: shading-lighting
  description: Materials, shading, lighting, and environment tools
  default_active: false
  tools:
  - add_toon_outline
  - create_toon_shader
  - list_toon_outlines
  - set_outline_width
---
# maya-toon

Non-photorealistic (NPR) toon shading utilities for Maya. Creates outline strokes,
surface shaders, and ramp-based fill shaders for cel-shading and stylized renders.

## Scripts

- `add_toon_outline` — Add a pfxToon outline stroke to selected meshes
- `create_toon_shader` — Create a ramp-based surface shader for cel shading
- `set_outline_width` — Adjust the line width of an existing pfxToon node
- `list_toon_outlines` — List all pfxToon nodes in the scene with linked meshes
