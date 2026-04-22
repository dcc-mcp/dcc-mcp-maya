---
name: maya-scene-assembly
description: Maya Scene Assembly — manage Assembly Definition, Assembly Reference, and level-of-detail workflows. Use when assembling large environments from asset references. Not for individual proxy creation or file referencing — use maya-proxy-mesh or maya-references for that.
license: MIT
allowed-tools: Bash Read
metadata:
  dcc-mcp:
    dcc: maya
    layer: domain
    version: 1.0.0
    tags:
    - maya
    - scene-assembly
    - lod
    - reference
    - pipeline
    - assembly
    search-hint: assemble environment, large scene, assembly definition, LOD workflow
    depends: []
    tools: tools.yaml
    groups: groups.yaml
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
