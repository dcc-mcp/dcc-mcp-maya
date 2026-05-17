---
name: maya-rigging
description: |-
  Authoring stage — character / prop rigging: joints, IK, skin clusters,
  deformers, blend shapes, and control curves. Use when constructing rigs.
  Not for keyframe animation (maya-animation), pose libraries
  (maya-pose-library), or final scene assembly (maya-scene-assembly).
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
    - rigging
    - skeleton
    - deformer
    - skin-cluster
    - blend-shape
    search-hint: |-
      build character rig, skeleton setup, IK chain, skin bind, blendshape,
      control curve, deformer, joint hierarchy, weight paint
    depends: []
    tools: tools.yaml
    groups: groups.yaml
---
# maya-rigging (Authoring stage)

Joint hierarchies, IK handles, skin clusters, deformers, blend shapes,
and control curves. Twelve scripts cover the typical rigging loop.
