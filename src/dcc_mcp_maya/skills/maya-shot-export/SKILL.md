---
name: maya-shot-export
description: Maya shot export — export shots, frame ranges, cameras, and FBX/Alembic for editorial. Use when packaging shot data for downstream departments. Not for full pipeline publishing or scene assembly — use maya-pipeline or maya-scene-assembly for that.
license: MIT
allowed-tools: Bash Read
metadata:
  dcc-mcp:
    dcc: maya
    layer: domain
    version: 1.0.0
    tags:
    - maya
    - export
    - shot
    - pipeline
    - production
    search-hint: package shot data, export frame range, editorial delivery
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
