---
name: maya-vertex-color
description: Maya vertex color and color set management
dcc: maya
version: 1.0.0
tags:
- maya
- vertex
- color
- paint
search-hint: vertex color, paint, color set, display
license: MIT
allowed-tools:
- Bash
- Read
depends: []
tools:
- name: create_color_set
- name: get_vertex_color
  read_only_hint: true
  idempotent_hint: true
- name: remove_vertex_colors
  destructive_hint: true
  idempotent_hint: true
- name: set_vertex_color
  idempotent_hint: true
groups:
- name: modeling
  description: Geometry creation, editing, and UV tools
  default_active: true
  tools:
  - create_color_set
  - get_vertex_color
  - remove_vertex_colors
  - set_vertex_color
---
