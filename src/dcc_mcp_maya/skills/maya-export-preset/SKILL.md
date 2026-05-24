---
name: maya-export-preset
description: |-
  Interchange stage — save / load / list / delete export presets (FBX, OBJ,
  Alembic configurations stored as JSON). Use to standardise export
  settings across a team or project. Not for one-off exports (use
  maya-geometry) or pipeline publishing (use maya-pipeline / maya-shot-export).
license: MIT
allowed-tools: Bash Read
metadata:
  dcc-mcp:
    dcc: maya
    layer: domain
    stage: interchange
    version: 1.1.0
    tags:
    - maya
    - export
    - preset
    - pipeline
    - fbx
    - alembic
    search-hint: |-
      standardize export, export preset, FBX preset, Alembic preset,
      load export config, save export config, share export settings
    tools: tools.yaml
---
# maya-export-preset (Interchange stage)

JSON-backed export preset management. Sits next to `maya-geometry` so
an agent can:

1. `maya-export-preset/load_export_preset` to materialise a saved
   FBX/OBJ/Alembic config, then
2. `maya-geometry/export_fbx` (or `maya-shot-export`) with those
   settings.

## Scripts

- `save_export_preset` — Persist current export settings as a JSON file
- `load_export_preset` — Load a JSON preset and return its parameter dict
- `list_export_presets` — List preset files in a directory
- `delete_export_preset` — Remove a preset file
