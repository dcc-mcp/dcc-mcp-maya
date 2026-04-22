---
name: maya-export-preset
description: Maya export preset management — save and load export configurations for FBX, OBJ, and Alembic. Use when standardizing export settings across a project. Not for one-off exports or pipeline publishing — use maya-scene or maya-pipeline for that.
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
    - preset
    - pipeline
    - fbx
    - alembic
    search-hint: standardize export, export configuration, FBX OBJ preset
    depends: []
    tools: tools.yaml
---
# Maya Export Preset Skill

Provides actions for saving, loading, listing and deleting Maya export presets (JSON-based configurations for FBX/Alembic export).
