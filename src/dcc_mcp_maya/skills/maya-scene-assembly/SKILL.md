---
name: maya-scene-assembly
description: |-
  Scene stage — Maya Scene Assembly workflow: Assembly Definitions, Assembly
  References, and LOD representation switching. Use for assembling large
  environments from cached / GPU / scene representations. Not for raw
  geometry import or referencing — use maya-geometry or execute_python with
  cmds.file(reference=True) instead.
license: MIT
allowed-tools: Bash Read
metadata:
  dcc-mcp:
    dcc: maya
    layer: domain
    stage: scene
    version: 1.0.0
    tags:
    - maya
    - scene-assembly
    - lod
    - reference
    - pipeline
    - assembly
    search-hint: |-
      assemble environment, large scene, assembly definition, assembly reference,
      LOD switch, representation swap, GPU cache representation
    depends: []
    tools: tools.yaml
    groups: groups.yaml
---
# maya-scene-assembly (Scene stage)

Maya Scene Assembly workflow. Wraps the
`assemblyDefinition` / `assemblyReference` node family so an agent can
assemble shots from cached / GPU / scene representations without manually
juggling the Scene Assembly menu.

## Scripts

- `create_assembly_definition` — Create an `assemblyDefinition` node
- `add_assembly_representation` — Add a representation (Locator, Cache, GPU, Scene) to an assembly
- `create_assembly_reference` — Instantiate an assembly definition into the scene
- `list_assemblies` — List all assembly definition and reference nodes
