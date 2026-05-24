---
name: maya-mesh-ops
description: |-
  Authoring stage — polygon mesh editing: bevel, extrude, bridge, combine,
  separate, cleanup, boolean. Use for modifying existing polygon topology.
  Not for primitive creation (use maya-primitives), construction-history or
  DG inspection (use maya-node-graph), UV layout (maya-uv-ops), or material
  assignment (maya-materials).
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
    - mesh
    - polygon
    - geometry
    - topology
    - bevel
    - extrude
    - boolean
    search-hint: |-
      edit mesh, modify polygons, bevel edge, extrude face, bridge, combine,
      separate, cleanup, boolean, subdivide, smooth topology
    tools: tools.yaml
    groups: groups.yaml
---
# maya-mesh-ops (Authoring stage)

Polygon mesh editing operations. Strictly **modifies existing polygon
topology**; all creation primitives live in `maya-primitives`, while
construction-history inspection belongs to `maya-node-graph`.

Each tool declares `affinity: main` because every operation touches
`maya.cmds`; the dispatcher schedules them on Maya's UI thread via
`MayaUiDispatcher`.
