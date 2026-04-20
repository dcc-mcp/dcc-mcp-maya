---
name: maya-lighting
description: Maya scene lighting — create, modify and query light nodes
dcc: maya
version: 1.0.0
tags:
- maya
- lighting
- light
- render
search-hint: light, directional, point, spot, area, ambient
license: MIT
allowed-tools:
- Bash
- Read
depends: []
tools:
- name: create_light
- name: delete_light
  destructive_hint: true
  idempotent_hint: true
- name: list_lights
  read_only_hint: true
  idempotent_hint: true
- name: set_light_attribute
  idempotent_hint: true
groups:
- name: shading-lighting
  description: Materials, shading, lighting, and environment tools
  default_active: false
  tools:
  - create_light
  - delete_light
  - list_lights
  - set_light_attribute
---
# maya-lighting

Maya lighting skill. Provides actions for creating lights (directional, point,
spot, area, ambient), adjusting light attributes, and listing all scene lights.

## Scripts

- `create_light` — Create a Maya light (directional, point, spot, area, ambient)
- `set_light_attribute` — Set a named attribute on a light node (intensity, color, shadows)
- `list_lights` — List all lights in the current scene with type and intensity
