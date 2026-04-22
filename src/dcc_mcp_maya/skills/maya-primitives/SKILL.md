---
name: maya-primitives
description: Maya polygon primitive creation and basic transform operations — spheres, cubes, cylinders, planes, and transforms. Use when creating individual basic geometry from scratch. Not for complex mesh editing, UV operations, or material assignment — use maya-mesh-ops, maya-uv-ops, or maya-materials for that.
license: MIT
allowed-tools: Bash Read
metadata:
  dcc-mcp:
    dcc: maya
    layer: domain
    version: 1.0.0
    tags:
    - maya
    - geometry
    - primitives
    - create
    search-hint: create basic geometry, add primitive, simple shape, individual mesh
    depends: []
    tools: tools.yaml
    groups: groups.yaml
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
