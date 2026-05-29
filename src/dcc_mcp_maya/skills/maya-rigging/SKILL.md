---
name: maya-rigging
description: |-
  Authoring stage — character / prop rigging: joints, IK, skin clusters,
  deformers, blend shapes, control curves, skin weights, constraints, and
  optional rig framework detection. Use when constructing rigs. Not for keyframe animation (maya-animation), pose libraries
  (maya-pose-library), or final scene assembly (maya-scene-assembly).
license: MIT
allowed-tools: Bash Read
metadata:
  dcc-mcp:
    dcc: maya
    layer: domain
    stage: authoring
    version: 1.2.0
    tags:
    - maya
    - rigging
    - skeleton
    - deformer
    - skin-cluster
    - blend-shape
    - skin-weights
    - constraint
    - mgear
    - rig-framework
    search-hint: |-
      build character rig, skeleton setup, IK chain, rig control, constraint,
      skin bind, skin weight copy, blendshape, control curve, mgear,
      advanced skeleton, deformer, joint hierarchy, weight paint,
      animated rig, rig for animation, make a rig, set up joints to animate
    tools: tools.yaml
    groups: groups.yaml
---
# maya-rigging (Authoring stage)

Joint hierarchies, IK handles, constraints, skin clusters, skin-weight transfer,
deformers, blend shapes, optional rig framework detection, and control curves.
Seventeen scripts cover the typical rigging loop.

## Optional Frameworks

Use `detect_rig_frameworks` before relying on optional packages such as mGear,
AdvancedSkeleton, MGTools, Go Skinning, Skin Magic, SI Weight Editor, or
MetaHuman-style DNA tools. Built-in rigging tools remain the default path; optional
frameworks are only used when detection reports `available=true`.
