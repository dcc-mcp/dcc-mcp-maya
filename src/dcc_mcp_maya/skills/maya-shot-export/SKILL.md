---
name: maya-shot-export
description: |-
  Pipeline stage — shot-level export: frame ranges, cameras, FBX / Alembic
  packaging for editorial. Use when packaging shot data for downstream
  departments. Not for full pipeline publish (maya-pipeline) or scene
  assembly (maya-scene-assembly).
license: MIT
allowed-tools: Bash Read
metadata:
  dcc-mcp:
    dcc: maya
    layer: domain
    stage: pipeline
    version: 1.1.0
    tags:
    - maya
    - export
    - shot
    - pipeline
    - production
    - alembic
    - fbx
    - editorial
    search-hint: |-
      shot export, package shot, export frame range, editorial delivery,
      shot camera FBX, shot Alembic, shot info
    aliases:
    - maya-shot-io
    side-effects:
    - reads-scene
    - reads-disk
    - writes-disk
    - calls-fbx-plugin
    depends:
    - maya-geometry
    tools: tools.yaml
---
# maya-shot-export (Pipeline stage)

Shot-level export utilities. Differs from `maya-geometry` in that it
encodes **shot conventions**: frame range, camera, sequence/shot
metadata. For raw FBX export of arbitrary geometry use `maya-geometry`.

## Scripts

- `export_shot_fbx` — Export selected geometry within a frame range to FBX
- `export_shot_alembic` — Export selected objects as Alembic (.abc) sequence
- `export_camera` — Export a shot camera to FBX or Maya ASCII
- `get_shot_info` — Query current shot metadata (frame range, camera, scene name)
