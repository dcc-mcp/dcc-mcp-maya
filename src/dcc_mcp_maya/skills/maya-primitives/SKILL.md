---
name: maya-primitives
description: "Maya polygon primitive creation and basic transform operations"
dcc: maya
version: "1.0.0"
tags: [maya, geometry, primitives, create]
license: "MIT"
allowed-tools: ["Bash", "Read"]
depends: []
tools:
  - name: create_sphere
    description: "Create a polygon sphere"
    source_file: scripts/create_sphere.py
    read_only: false
    destructive: false
    idempotent: false
  - name: create_cube
    description: "Create a polygon cube"
    source_file: scripts/create_cube.py
    read_only: false
    destructive: false
    idempotent: false
  - name: create_cylinder
    description: "Create a polygon cylinder"
    source_file: scripts/create_cylinder.py
    read_only: false
    destructive: false
    idempotent: false
  - name: create_plane
    description: "Create a polygon plane"
    source_file: scripts/create_plane.py
    read_only: false
    destructive: false
    idempotent: false
  - name: delete_objects
    description: "Delete objects from the Maya scene"
    source_file: scripts/delete_objects.py
    read_only: false
    destructive: true
    idempotent: false
  - name: set_transform
    description: "Set translate/rotate/scale on an object"
    source_file: scripts/set_transform.py
    read_only: false
    destructive: false
    idempotent: true
  - name: get_transform
    description: "Get translate/rotate/scale of an object"
    source_file: scripts/get_transform.py
    read_only: true
    destructive: false
    idempotent: true
  - name: rename_object
    description: "Rename an object in the scene"
    source_file: scripts/rename_object.py
    read_only: false
    destructive: false
    idempotent: true
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
