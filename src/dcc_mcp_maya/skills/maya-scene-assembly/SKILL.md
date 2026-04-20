---
name: maya-scene-assembly
description: Maya Scene Assembly — manage Assembly Definition, Assembly Reference, and representation LODs
dcc: maya
tags:
- scene-assembly
- LOD
- reference
- pipeline
- assembly
search-hint: scene assembly, asset, level, publish
version: 1.0.0
license: MIT
allowed-tools:
- Bash
- Read
depends: []
tools:
- name: add_assembly_representation
- name: create_assembly_definition
- name: create_assembly_reference
- name: list_assemblies
  read_only_hint: true
  idempotent_hint: true
groups:
- name: scene-management
  description: Scene management, organization, and navigation tools
  default_active: true
  tools:
  - add_assembly_representation
  - create_assembly_definition
  - create_assembly_reference
  - list_assemblies
---
# maya-scene-assembly

Maya Scene Assembly skill. Provides actions for creating Assembly Definitions,
instancing Assembly References into the scene, switching LOD representations,
and listing assembly nodes.

## Scripts

- `create_assembly_definition` — Create an assemblyDefinition node
- `add_assembly_representation` — Add a representation (Locator, Cache, GPU, Scene) to an assembly
- `create_assembly_reference` — Instantiate an assembly definition into the scene
- `list_assemblies` — List all assembly definition and reference nodes
