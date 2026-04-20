---
name: maya-expressions
description: Maya expression nodes — create, list and delete procedural expressions
dcc: maya
version: 1.0.0
tags:
- maya
- expression
- scripting
- procedural
search-hint: expression, script, attribute, driven key
license: MIT
allowed-tools:
- Bash
- Read
depends: []
tools:
- name: create_expression
- name: delete_expression
  destructive_hint: true
  idempotent_hint: true
- name: edit_expression
- name: list_expressions
  read_only_hint: true
  idempotent_hint: true
groups:
- name: animation
  description: Animation, constraints, and motion capture tools
  default_active: false
  tools:
  - create_expression
  - delete_expression
  - edit_expression
  - list_expressions
---
# maya-expressions

Maya expressions skill. Provides actions for creating, listing, and deleting Maya expression nodes.

## Scripts

- `create_expression` — Create a Maya expression node
- `list_expressions` — List Maya expression nodes in the scene
- `delete_expression` — Delete a Maya expression node by name
