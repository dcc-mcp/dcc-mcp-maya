---
name: maya-utility
description: Maya utility nodes and scene statistics
dcc: maya
version: 1.0.0
tags:
- maya
- utility
- node
- scene
search-hint: utility, transform, freeze, center pivot, convert
license: MIT
allowed-tools:
- Bash
- Read
depends: []
tools:
- name: clean_scene
- name: create_utility_node
- name: get_scene_statistics
  read_only_hint: true
  idempotent_hint: true
- name: list_node_connections
  read_only_hint: true
  idempotent_hint: true
---
# maya-utility

Maya utility skill. Provides actions for creating utility/shading nodes and querying scene statistics.

## Scripts

- `create_utility_node` — Create any Maya utility or shading node by type
- `get_scene_statistics` — Query scene-level statistics: polygon counts, node counts and memory
