---
name: maya-constraints
description: Maya constraints — parent, point, orient, scale, aim and weighted constraints
dcc: maya
version: 1.0.0
tags:
- maya
- constraint
- rigging
search-hint: constraint, parent, orient, aim, point, scale
license: MIT
allowed-tools:
- Bash
- Read
depends: []
tools:
- name: add_constraint
- name: create_constraint_weighted
- name: list_constraints
  read_only_hint: true
  idempotent_hint: true
- name: remove_constraint
  destructive_hint: true
  idempotent_hint: true
groups:
- name: animation
  description: Animation, constraints, and motion capture tools
  default_active: false
  tools:
  - add_constraint
  - create_constraint_weighted
  - list_constraints
  - remove_constraint
---
# maya-constraints

Maya constraints skill. Provides actions for adding, removing, listing, and
creating weighted constraints on Maya objects.

## Scripts

- `add_constraint` — Add a Maya constraint from source to target
- `remove_constraint` — Remove constraint(s) from a target object
- `list_constraints` — List all constraints applied to a target object
- `create_constraint_weighted` — Create a weighted multi-source constraint
