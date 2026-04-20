---
name: maya-xgen
description: Maya XGen hair and fur operations — create, list, preview and manage XGen descriptions
dcc: maya
version: 1.0.0
tags:
- maya
- xgen
- hair
- fur
- grooming
search-hint: xgen, hair, fur, feather, groom
license: MIT
allowed-tools:
- Bash
- Read
depends: []
tools:
- name: create_description
- name: delete_description
  destructive_hint: true
  idempotent_hint: true
- name: get_xgen_attribute
  read_only_hint: true
  idempotent_hint: true
- name: list_descriptions
  read_only_hint: true
  idempotent_hint: true
- name: set_xgen_attribute
  idempotent_hint: true
groups:
- name: simulation-fx
  description: Dynamics, simulation, particles, and VFX tools
  default_active: false
  tools:
  - create_description
  - delete_description
  - get_xgen_attribute
  - list_descriptions
  - set_xgen_attribute
---
# maya-xgen

Maya XGen skill. Provides actions for creating and managing XGen hair/fur descriptions,
controlling groom modifiers, and querying XGen collections.

## Scripts

- `create_description` — Create an XGen description on a mesh
- `list_descriptions` — List all XGen descriptions in the scene
- `delete_description` — Delete an XGen description
- `set_xgen_attribute` — Set an attribute on an XGen description or modifier
- `get_xgen_attribute` — Get an attribute value from an XGen description
