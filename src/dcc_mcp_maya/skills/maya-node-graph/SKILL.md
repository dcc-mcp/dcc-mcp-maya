---
name: maya-node-graph
description: Maya node graph — connect/disconnect attributes, query history and topology
dcc: maya
version: 1.0.0
tags:
- maya
- node
- attribute
- graph
- utility
search-hint: node, graph, connection, attribute, editor
license: MIT
allowed-tools:
- Bash
- Read
depends: []
tools:
- name: apply_symmetry
  idempotent_hint: true
- name: connect_attr
- name: delete_history
  destructive_hint: true
  idempotent_hint: true
- name: disconnect_attr
- name: get_dag_path
  read_only_hint: true
  idempotent_hint: true
- name: list_connections
  read_only_hint: true
  idempotent_hint: true
- name: list_history
  read_only_hint: true
  idempotent_hint: true
- name: smooth_mesh
- name: transfer_attributes
---
# maya-node-graph

Maya node graph skill. Provides actions for connecting and disconnecting attributes, querying history, and managing mesh topology.

## Scripts

- `connect_attr` — Connect two Maya node attributes
- `disconnect_attr` — Disconnect two connected Maya node attributes
- `list_connections` — List nodes/attributes connected to a Maya node or attribute
- `get_dag_path` — Return the full DAG path of a Maya node
- `smooth_mesh` — Apply smooth mesh preview or subdivision to a polygon mesh
- `list_history` — List construction history nodes for a Maya object
- `delete_history` — Delete the construction history on a Maya object
- `apply_symmetry` — Apply mesh symmetry to a polygon object
- `transfer_attributes` — Transfer mesh attributes (UVs, normals, vertex colors) from one mesh to another
