---
name: maya-geometry
description: End-to-end geometry export workflow tools for saving scenes and writing FBX/OBJ interchange files. Use maya-primitives for primitive creation.
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
    search-hint: save Maya scene, export FBX OBJ, check output file, geometry workflow
    depends: []
    tools: tools.yaml
    groups: groups.yaml
---
# maya-geometry

Maya geometry workflow tools for saving scene data and exporting FBX/OBJ interchange files. For individual primitive creation, use `maya-primitives`.

## Groups

- **core** — File-system checks that do not touch Maya state.
- **geometry** — Main-thread Maya scene save and interchange export operations.

## Scripts

- `save_scene` — Save the current scene as Maya ASCII or Maya Binary.
- `file_exists` — Check whether a file exists on disk.
- `export_fbx` — Export the scene or current selection to FBX.
- `export_obj` — Export the scene to OBJ.
