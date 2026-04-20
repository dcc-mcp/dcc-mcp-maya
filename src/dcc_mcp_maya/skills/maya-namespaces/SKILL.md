---
name: maya-namespaces
description: Maya namespace management — create, rename, merge, and remove namespaces for asset organization
dcc: maya
version: 1.0.0
tags:
- maya
- namespaces
- pipeline
- rigging
- scene-management
search-hint: namespace, reference, scene, organize
license: MIT
allowed-tools:
- Bash
- Read
depends: []
tools:
- name: create_namespace
- name: delete_namespace
  destructive_hint: true
  idempotent_hint: true
- name: list_namespaces
  read_only_hint: true
  idempotent_hint: true
- name: remove_namespace
  destructive_hint: true
  idempotent_hint: true
- name: rename_namespace
  idempotent_hint: true
- name: set_namespace
  idempotent_hint: true
groups:
- name: scene-management
  description: Scene management, organization, and navigation tools
  default_active: true
  tools:
  - create_namespace
  - delete_namespace
  - list_namespaces
  - remove_namespace
  - rename_namespace
  - set_namespace
---
# maya-namespaces

Namespace utilities for Maya pipeline workflows. Manage asset namespaces for clean
scene organization, referencing, and rigging.

## Scripts

- `create_namespace` — Create a new namespace (optionally nested)
- `list_namespaces` — List all non-default namespaces with object counts
- `rename_namespace` — Rename an existing namespace
- `remove_namespace` — Remove a namespace (merge contents into parent)
