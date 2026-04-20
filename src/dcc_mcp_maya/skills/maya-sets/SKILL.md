---
name: maya-sets
description: Maya object sets — create, add to, remove from and list Maya sets
dcc: maya
version: 1.0.0
tags:
- maya
- set
- collection
- utility
search-hint: set, group, partition, render, deformer set
license: MIT
allowed-tools:
- Bash
- Read
depends: []
tools:
- name: add_to_set
- name: create_set
- name: list_sets
  read_only_hint: true
  idempotent_hint: true
- name: remove_from_set
  destructive_hint: true
  idempotent_hint: true
groups:
- name: scene-management
  description: Scene management, organization, and navigation tools
  default_active: true
  tools:
  - add_to_set
  - create_set
  - list_sets
  - remove_from_set
---
# maya-sets

Maya sets skill. Provides actions for creating, managing, and listing Maya object sets.

## Scripts

- `create_set` — Create a Maya object set
- `add_to_set` — Add objects to an existing Maya object set
- `remove_from_set` — Remove objects from an existing Maya object set
- `list_sets` — List all Maya object sets in the scene
