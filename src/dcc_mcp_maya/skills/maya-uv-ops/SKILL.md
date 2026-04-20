---
name: maya-uv-ops
description: Maya UV operations — create, delete, project, unfold and normalize UV layouts
dcc: maya
version: 1.0.0
tags:
- maya
- uv
- texture
- geometry
search-hint: UV, unfold, layout, planar map, texture coordinates
license: MIT
allowed-tools:
- Bash
- Read
depends: []
tools:
- name: copy_uvs
- name: create_uv_set
- name: delete_uv_set
  destructive_hint: true
  idempotent_hint: true
- name: get_uv_info
  read_only_hint: true
  idempotent_hint: true
- name: get_uv_shell_info
  read_only_hint: true
  idempotent_hint: true
- name: normalize_uvs
- name: project_uvs
- name: unfold_uvs
groups:
- name: modeling
  description: Geometry creation, editing, and UV tools
  default_active: true
  tools:
  - copy_uvs
  - create_uv_set
  - delete_uv_set
  - get_uv_info
  - get_uv_shell_info
  - normalize_uvs
  - project_uvs
  - unfold_uvs
---
