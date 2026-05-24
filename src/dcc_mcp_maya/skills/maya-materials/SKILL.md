---
name: maya-materials
description: |-
  Authoring stage — create, assign, query, and manage Lambert / Blinn /
  surface shader networks. Use for ad-hoc material assignment. For reusable
  presets and library workflows use maya-material-library; for final
  rendering use maya-render.
license: MIT
allowed-tools: Bash Read
metadata:
  dcc-mcp:
    dcc: maya
    layer: domain
    stage: authoring
    version: 1.1.0
    tags:
    - maya
    - material
    - shader
    - shading
    - lambert
    - blinn
    search-hint: |-
      assign shader, basic material, surface shader, lambert blinn,
      create material, shading group, shadingEngine, sets surfaceShader
    tools: tools.yaml
    groups: groups.yaml
---
# maya-materials (Authoring stage)

Build and assign basic shader networks. Eight scripts cover the typical
"create a Lambert and assign it" loop while keeping `inputSchema`
validation in place.

For sharing material presets across assets / shots, use
`maya-material-library`.
