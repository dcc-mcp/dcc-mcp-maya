---
name: maya-export-preset
description: Maya export preset management actions for saving and loading export configurations
license: MIT
allowed-tools: Bash Read
metadata:
  dcc-mcp:
    dcc: maya
    version: 1.0.0
    tags:
    - maya
    - export
    - preset
    - pipeline
    - fbx
    - alembic
    search-hint: export, preset, format, fbx, obj
    depends: []
    tools: tools.yaml
---
# Maya Export Preset Skill

Provides actions for saving, loading, listing and deleting Maya export presets (JSON-based configurations for FBX/Alembic export).
