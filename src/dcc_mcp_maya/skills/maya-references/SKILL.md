---
name: maya-references
description: Maya file references and namespace management
dcc: maya
version: 1.0.0
tags:
- maya
- reference
- namespace
- scene
search-hint: reference, import, namespace, link, file
license: MIT
allowed-tools:
- Bash
- Read
depends: []
tools:
- name: create_reference
- name: list_namespaces
  read_only_hint: true
  idempotent_hint: true
- name: list_references
  read_only_hint: true
  idempotent_hint: true
- name: reload_reference
- name: remove_reference
  destructive_hint: true
  idempotent_hint: true
- name: unload_reference
groups:
- name: scene-management
  description: Scene management, organization, and navigation tools
  default_active: true
  tools:
  - create_reference
  - list_namespaces
  - list_references
  - reload_reference
  - remove_reference
  - unload_reference
---
# maya-references

Maya references skill. Provides actions for creating, listing, removing, reloading, and unloading file references, as well as listing namespaces.

## Scripts

- `create_reference` — Reference an external Maya file into the current scene
- `list_references` — List all file references in the current scene
- `remove_reference` — Remove a file reference from the current scene
- `reload_reference` — Reload a previously unloaded (or modified) file reference
- `unload_reference` — Unload a file reference without removing it from the scene
- `list_namespaces` — List all namespaces in the current scene
