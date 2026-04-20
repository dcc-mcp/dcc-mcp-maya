---
name: maya-export-preset
description: Maya export preset management actions for saving and loading export configurations
dcc: maya
tags:
- export
- preset
- pipeline
- fbx
- alembic
search-hint: export, preset, format, fbx, obj
version: 1.0.0
license: MIT
allowed-tools:
- Bash
- Read
depends: []
tools:
- name: delete_export_preset
  destructive_hint: true
  idempotent_hint: true
- name: list_export_presets
  read_only_hint: true
  idempotent_hint: true
- name: load_export_preset
- name: save_export_preset
---
# Maya Export Preset Skill

Provides actions for saving, loading, listing and deleting Maya export presets (JSON-based configurations for FBX/Alembic export).
