---
name: maya-display
description: Maya display layers and viewport shading mode management
dcc: maya
version: 1.0.0
tags:
- maya
- display
- layer
- visibility
search-hint: display, visibility, show, hide, wireframe, layer
license: MIT
allowed-tools:
- Bash
- Read
depends: []
tools:
- name: create_display_layer
- name: delete_display_layer
  destructive_hint: true
  idempotent_hint: true
- name: list_display_layers
  read_only_hint: true
  idempotent_hint: true
- name: set_display_layer
  idempotent_hint: true
groups:
- name: scene-management
  description: Scene management, organization, and navigation tools
  default_active: true
  tools:
  - create_display_layer
  - delete_display_layer
  - list_display_layers
  - set_display_layer
---
# maya-display

Maya display skill. Provides actions for creating, setting, deleting, and listing display layers in Maya.

## Scripts

- `create_display_layer` — Create a display layer and optionally add objects to it
- `set_display_layer` — Assign an object to an existing display layer
- `delete_display_layer` — Delete a display layer
- `list_display_layers` — List all display layers in the scene
