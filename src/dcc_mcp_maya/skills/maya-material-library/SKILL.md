---
name: maya-material-library
description: Maya material library — save, load, and manage reusable material presets stored as JSON or Maya files
dcc: maya
version: 1.0.0
tags:
- maya
- materials
- library
- shading
- presets
search-hint: material, library, shader, preset
license: MIT
allowed-tools:
- Bash
- Read
depends: []
tools:
- name: delete_material_preset
  destructive_hint: true
  idempotent_hint: true
- name: list_materials
  read_only_hint: true
  idempotent_hint: true
- name: load_material
- name: save_material
groups:
- name: shading-lighting
  description: Materials, shading, lighting, and environment tools
  default_active: false
  tools:
  - delete_material_preset
  - list_materials
  - load_material
  - save_material
---
# maya-material-library

Reusable material preset management for Maya. Saves shader networks to a JSON
library and restores them, enabling consistent look-dev across shots and assets.

## Scripts

- `save_material` — Serialize a material and its attributes to a JSON preset file
- `load_material` — Recreate a material from a JSON preset and assign it optionally
- `list_materials` — List all preset files in a material library directory
- `delete_material_preset` — Remove a material preset file from the library
