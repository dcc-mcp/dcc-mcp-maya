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

## Joint Placement and Orientation

When reviewing or editing joints, distinguish **pivot placement**, **joint
orientation (including roll)**, and the rotate tool's display mode. A gizmo in
World or Object mode is not sufficient evidence that a joint will bend correctly.
Inspect local rotation axes and test the intended motion; zeroing rotation
channels alone does not repair an incorrect pivot or `jointOrient`.

- Inspect the mesh and joint in multiple views. Place a hinge at the intended
  articulation center, using anatomical landmarks or a mechanical joint's
  geometry rather than the mesh bounding-box center. Do not move a correctly
  placed pivot merely to change its axes.
- Aiming at the next joint establishes a length direction, but does not resolve
  roll around that direction. Check the intended bend plane against the mesh,
  not only the existing joint chain. Mesh cross-section centers or other clear
  landmarks can help, but uneven sampling and asymmetry can bias them. A straight
  centerline does not uniquely define a bend plane: request a reference or user
  clarification instead of guessing.
- Respect the rig's aim/curl-axis conventions. Do not assume a universal world
  axis, naming scheme, finger-length percentage, or left/right rotation sign.
  Check each joint and mirrored side independently; thumbs and terminal joints
  may need different references from the other fingers.
- For a requested correction, explain whether placement, orientation, or both
  will change. Save a recoverable scene checkpoint before editing. Validate one
  representative joint with the user before repeating an uncertain correction
  across a chain. A request to inspect is not permission to rebuild joints.
- On an existing rig, inspect skin bindings, bind-pose records, animation,
  constraints, and child transforms before changing placement or orientation.
  Do not blindly freeze transforms, delete/recreate joints, detach skin, or
  reset bind records. Use a method appropriate to that rig that preserves the
  intended rest shape, skin weights, hierarchy, and child world transforms;
  stop and explain if those invariants cannot be maintained safely. Do not
  silently change the bind state of a posed or animated rig.
- Verify with a small isolated bend around the intended local axis, then return
  to the original pose and time. Check the motion against the mesh's bend plane,
  descendant positions, and skin deformation—not just a static gizmo screenshot.
  Confirm that weights and the rest shape remain intact after the edit. If the
  result is wrong, restore the checkpoint or undo and reassess the reference
  rather than repeatedly applying guessed orientations. Report what changed,
  what was verified, and any uncertainty; separate remaining weight-painting
  problems from placement or orientation problems.

## Optional Frameworks

Use `detect_rig_frameworks` before relying on optional packages such as mGear,
AdvancedSkeleton, MGTools, Go Skinning, Skin Magic, SI Weight Editor, or
MetaHuman-style DNA tools. Built-in rigging tools remain the default path; optional
frameworks are only used when detection reports `available=true`.
