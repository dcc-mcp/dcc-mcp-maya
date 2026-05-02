---
name: maya-geometry
description: Maya geometry creation and export tools for simple mesh primitives and scene interchange files.
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
    - mesh
    - export
    search-hint: create sphere, save Maya scene, export FBX OBJ, check output file
    depends: []
    tools: tools.yaml
    groups: groups.yaml
---
# maya-geometry

Maya geometry tools for creating simple mesh primitives and exporting scene data.

## Groups

- **core** — File-system checks that do not touch Maya state.
- **geometry** — Main-thread Maya geometry creation and export operations.

## Scripts

- `create_sphere` — Create a polygon sphere.
- `save_scene` — Save the current scene as Maya ASCII or Maya Binary.
- `file_exists` — Check whether a file exists on disk.
- `export_fbx` — Export the scene or current selection to FBX.
- `export_obj` — Export the scene to OBJ.
