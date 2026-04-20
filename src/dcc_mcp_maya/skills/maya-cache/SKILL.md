---
name: maya-cache
description: Maya geometry cache — create, attach, list and delete geometry caches for mesh deformations
dcc: maya
version: 1.0.0
tags:
- maya
- cache
- geometry
- simulation
search-hint: cache, geometry cache, bake, deformation
license: MIT
allowed-tools:
- Bash
- Read
depends: []
tools:
- name: attach_geometry_cache
- name: create_geometry_cache
- name: delete_geometry_cache
  destructive_hint: true
  idempotent_hint: true
- name: list_geometry_caches
  read_only_hint: true
  idempotent_hint: true
---
# maya-cache

Maya cache skill. Provides actions for baking geometry deformations to disk cache
files and attaching cached data back to meshes. Useful for preserving simulations
and speeding up playback.

## Scripts

- `create_geometry_cache` — Bake geometry deformations to a disk cache file
- `attach_geometry_cache` — Attach an existing cache file to a mesh
- `list_geometry_caches` — List cache nodes attached to a mesh
- `delete_geometry_cache` — Delete a geometry cache node and optionally its files
