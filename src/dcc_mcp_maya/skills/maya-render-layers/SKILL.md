---
name: maya-render-layers
description: Maya render layers — create, assign, list and manage render layer overrides
dcc: maya
version: 1.0.0
tags:
- maya
- render
- layer
- renderlayer
search-hint: render layer, override, pass, layer
license: MIT
allowed-tools:
- Bash
- Read
depends: []
tools:
- name: create_render_layer
- name: delete_render_layer
  destructive_hint: true
  idempotent_hint: true
- name: list_render_layers
  read_only_hint: true
  idempotent_hint: true
- name: set_render_layer
  idempotent_hint: true
- name: set_render_layer_attribute
  idempotent_hint: true
groups:
- name: rendering
  description: Render settings, layers, passes, and output tools
  default_active: false
  tools:
  - create_render_layer
  - delete_render_layer
  - list_render_layers
  - set_render_layer
  - set_render_layer_attribute
---
# maya-render-layers

Maya render layers skill. Provides actions for creating, assigning, listing, deleting render layers and setting render layer attribute overrides.

## Scripts

- `create_render_layer` — Create a render layer and optionally add objects to it
- `set_render_layer` — Assign an object to an existing render layer
- `list_render_layers` — List all render layers in the scene
- `delete_render_layer` — Delete a render layer from the scene
- `set_render_layer_attribute` — Set an attribute override on a render layer node
