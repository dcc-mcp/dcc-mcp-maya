---
name: maya-mash
description: Maya MASH motion graphics network — create, modify and query MASH networks
dcc: maya
version: 1.0.0
tags:
- maya
- mash
- motion-graphics
- instancer
- dynamics
search-hint: mash, motion graphics, distribute, scatter
license: MIT
allowed-tools:
- Bash
- Read
depends: []
tools:
- name: add_node
- name: create_network
- name: delete_network
  destructive_hint: true
  idempotent_hint: true
- name: list_networks
  read_only_hint: true
  idempotent_hint: true
- name: set_mash_attribute
  idempotent_hint: true
groups:
- name: simulation-fx
  description: Dynamics, simulation, particles, and VFX tools
  default_active: false
  tools:
  - add_node
  - create_network
  - delete_network
  - list_networks
  - set_mash_attribute
---
# maya-mash

Maya MASH skill. Provides actions for creating and managing MASH networks for
motion graphics, instancing, and procedural animation.

## Scripts

- `create_network` — Create a MASH network for an object
- `list_networks` — List all MASH networks in the scene
- `delete_network` — Delete a MASH network
- `add_node` — Add a MASH node to an existing network
- `set_mash_attribute` — Set an attribute on a MASH node
