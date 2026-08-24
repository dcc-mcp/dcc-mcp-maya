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
    version: 1.4.0
    tags:
    - maya
    - rigging
    - skeleton
    - deformer
    - skin-cluster
    - blend-shape
    - skin-weights
    - constraint
    - hair
    - guide-curve
    - mgear
    - rig-framework
    search-hint: |-
      build character rig, skeleton setup, IK chain, rig control, constraint,
      skin bind, skin weight copy, blendshape, control curve, mgear,
      advanced skeleton, deformer, joint hierarchy, weight paint, editable
      hair guide curve, colored guide cluster, scalp root projection
    tools: tools.yaml
    groups: groups.yaml
---
# maya-rigging (Authoring stage)

Joint hierarchies, IK handles, constraints, skin clusters, skin-weight transfer,
deformers, blend shapes, optional rig framework detection, control curves, and
editable hair guide curves. Twenty-one scripts cover the typical rigging loop.

`get_skin_weights` reads an explicit bounded vertex subset (or the whole mesh
when it fits the limit) and reports per-vertex totals plus an
`unnormalized_vertices` count. It never silently truncates a large mesh.
`set_skin_weights` accepts only complete normalized rows for known influences,
clears omitted influence values on those vertices, and verifies every effective
native value before reporting success.
`export_rig_state` deterministically reports bounded joint hierarchy,
constraints, NURBS controls, and per-skin normalization health. Large rigs fail
closed instead of returning a partial snapshot.

`create_guide_curve` is the bounded guide-authoring contract: every open curve
has one cluster ID, one solid RGB viewport color, root-to-tip CV order, arc
length and cluster-median deviation metrics, and an optional measured root
projection distance against an explicit scalp mesh. It accepts only named
metadata fields (`source_view` and `dominant_clump`), never arbitrary script or
metadata payloads. The general-purpose `create_curve` contract remains
unchanged.

## Optional Frameworks

Use `detect_rig_frameworks` before relying on optional packages such as mGear,
AdvancedSkeleton, MGTools, Go Skinning, Skin Magic, SI Weight Editor, or
MetaHuman-style DNA tools. Built-in rigging tools remain the default path; optional
frameworks are only used when detection reports `available=true`.
