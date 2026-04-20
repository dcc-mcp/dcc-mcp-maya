---
name: maya-primitives
description: Maya polygon primitive creation and basic transform operations
dcc: maya
version: 1.0.0
tags:
- maya
- geometry
- primitives
- create
search-hint: create, sphere, cube, plane, cylinder, primitive, polygon
license: MIT
allowed-tools:
- Bash
- Read
depends: []
tools:
- name: create_cube
  description: Create a polygon cube
- name: create_cylinder
  description: Create a polygon cylinder
- name: create_plane
  description: Create a polygon plane
- name: create_sphere
  description: Create a polygon sphere
- name: delete_objects
  description: Delete objects from the Maya scene
  destructive_hint: true
  idempotent_hint: true
- name: get_transform
  description: Get translate/rotate/scale of an object
  read_only_hint: true
  idempotent_hint: true
- name: rename_object
  description: Rename an object in the scene
  idempotent_hint: true
- name: set_transform
  description: Set translate/rotate/scale on an object
  idempotent_hint: true
groups:
- name: modeling
  description: Geometry creation, editing, and UV tools
  default_active: true
  tools:
  - create_cube
  - create_cylinder
  - create_plane
  - create_sphere
  - delete_objects
  - get_transform
  - rename_object
  - set_transform
---
# maya-primitives

Maya polygon primitive creation skill. Provides actions for creating basic geometry (sphere, cube, cylinder, plane), deleting objects, and managing transforms.

## Scripts

- `create_sphere` — Create a polygon sphere
- `create_cube` — Create a polygon cube
- `create_cylinder` — Create a polygon cylinder
- `create_plane` — Create a polygon plane
- `delete_objects` — Delete objects from the Maya scene
- `set_transform` — Set translate/rotate/scale on an object
- `get_transform` — Get translate/rotate/scale of an object
- `rename_object` — Rename an object in the scene
