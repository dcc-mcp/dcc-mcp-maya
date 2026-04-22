---
name: maya-shot-export
description: Maya shot export — export shots, frame ranges, cameras, and FBX/Alembic
  sequences for production pipelines
license: MIT
allowed-tools: Bash Read
metadata:
  dcc-mcp:
    dcc: maya
    version: 1.0.0
    tags:
    - maya
    - export
    - shot
    - pipeline
    - production
    search-hint: shot, export, sequence, frame range, publish
    depends: []
    tools: tools.yaml
---
# maya-shot-export

Shot-level export utilities for Maya production pipelines. Exports frame ranges,
cameras, and geometry sequences in FBX or Alembic format with shot metadata.

## Scripts

- `export_shot_fbx` — Export selected geometry within a frame range to FBX
- `export_shot_alembic` — Export selected objects as Alembic (.abc) sequence
- `export_camera` — Export a shot camera to FBX or Maya ASCII
- `get_shot_info` — Query current shot metadata (frame range, camera, scene name)
