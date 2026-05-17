---
name: maya-uv-ops
description: |-
  Authoring stage — UV operations: create, delete, project, unfold, layout,
  and normalise UV sets. Use whenever working on texture coordinates. Not
  for mesh modeling (maya-mesh-ops), material authoring (maya-materials),
  or texture baking (maya-texture-bake).
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
    - uv
    - texture
    - geometry
    search-hint: |-
      layout UVs, unfold UV, texture coordinates, UV projection, automatic UV,
      planar projection, UV set, normalize UV
    depends: []
    tools: tools.yaml
    groups: groups.yaml
---
# maya-uv-ops (Authoring stage)

UV-set authoring tools. All eight scripts are main-thread-affine because
they touch UV nodes through `maya.cmds`.
