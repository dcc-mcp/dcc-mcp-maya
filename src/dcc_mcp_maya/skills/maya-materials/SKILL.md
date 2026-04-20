---
name: maya-materials
description: Maya shading materials — create, assign, query and manage material networks
dcc: maya
version: 1.0.0
tags:
- maya
- material
- shader
- shading
search-hint: material, shader, lambert, blinn, assign, surface
license: MIT
allowed-tools:
- Bash
- Read
depends: []
tools:
- name: assign_material
  idempotent_hint: true
- name: create_material
- name: get_material_connections
  read_only_hint: true
  idempotent_hint: true
- name: get_shader_assignment
  read_only_hint: true
  idempotent_hint: true
- name: list_materials
  read_only_hint: true
  idempotent_hint: true
- name: list_shading_groups
  read_only_hint: true
  idempotent_hint: true
- name: reset_to_default_material
  idempotent_hint: true
- name: set_material_attribute
  idempotent_hint: true
groups:
- name: shading-lighting
  description: Materials, shading, lighting, and environment tools
  default_active: false
  tools:
  - assign_material
  - create_material
  - get_material_connections
  - get_shader_assignment
  - list_materials
  - list_shading_groups
  - reset_to_default_material
  - set_material_attribute
---
