---
name: maya-scene-assembly
description: Maya Scene Assembly — manage Assembly Definition, Assembly Reference, and representation LODs
dcc: maya
tags: [scene-assembly, LOD, reference, pipeline, assembly]
version: "1.0.0"
license: "MIT"
allowed-tools: ["Bash", "Read"]
depends: []
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
