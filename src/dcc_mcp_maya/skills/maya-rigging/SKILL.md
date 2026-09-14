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
      hair guide curve, colored guide cluster, scalp root projection, joint
      orientation, local rotation axes, aim axis, joint roll, bend plane
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

Treat joint orientation as the design of a local coordinate frame, not as a
cosmetic cleanup operation. Keep these concepts separate:

- **Position** places the pivot where rotation should occur.
- **Aim** points one chosen local axis toward the primary child.
- **Roll** rotates the remaining two axes around the aim axis and determines the
  bend plane.
- **`jointOrient`** stores the rest orientation; animation normally belongs in
  `rotate`. Non-zero `jointOrient` values are expected and are not an error.
- The rotate manipulator's World or Object display mode is not evidence of the
  joint's local rotation axes.

Use this decision process whenever creating, reviewing, or repairing a chain:

1. **Establish context before editing.** Inspect the hierarchy, transforms,
   local rotation axes, constraints, animation, skin clusters, and bind-pose
   records. An inspection request is not permission to rebuild a chain. On an
   established rig, make a recoverable checkpoint and identify the state that
   must be preserved.
2. **Identify the intended motion.** Determine each pivot, the primary child,
   the expected degrees of freedom, and any intended bend plane. Derive this
   from the asset, rig specification, or user-provided reference. A perfectly
   straight chain does not define a stable bend direction; do not invent one.
3. **Choose or discover the convention.** Record the aim axis, secondary axis,
   axis sign, handedness, and mirror behavior. Existing rig conventions take
   precedence. There is no universal Maya axis or Euler-sign convention, but a
   continuous chain should use one documented convention consistently unless a
   deliberate exception is required.
4. **Place pivots first.** Position joints at the intended articulation centers
   and inspect them from multiple views. Do not move a correct pivot merely to
   repair its axes. Give solver-driven hinge chains a small intentional pre-bend
   in their expected plane when the design permits it.
5. **Solve aim and roll separately.** Aim the parent at its primary child, then
   resolve roll from a stable secondary-axis reference or known bend plane.
   Aiming alone cannot determine roll. At a branching joint, aim toward the
   designated primary child; orient each branch from its own requirements.
6. **Store a clean rest state.** Put the rest orientation in `jointOrient` and
   keep `rotate` at zero. Keep `rotateAxis` and scale at their neutral values
   unless the rig explicitly uses them. Do not blindly freeze transforms,
   delete and recreate joints, detach skin, or rewrite bind records to obtain
   zero channels.
7. **Handle terminal and mirrored joints deliberately.** A terminal joint has no
   child from which to derive an aim; match a documented parent/world convention
   or leave its orientation neutral. Validate mirrored behavior by equivalent
   motion, not by assuming both sides must have identical Euler values.

Validate the result with independent evidence:

- Confirm the hierarchy, primary-child choices, pivot positions, and absence of
  accidental duplicate or coincident joints.
- Confirm rest `rotate` values are zero and scales are neutral, except for
  intentional, documented rig features.
- In an aim-axis-aligned chain, each child's local translation should lie almost
  entirely on the chosen aim axis with a consistent sign. Off-axis values should
  be explainable by an intentional exception.
- Display local rotation axes and compare neighboring frames for unexpected
  flips or roll discontinuities.
- Apply small isolated rotations around each intended local axis, observe the
  pivot, bend plane, descendants, and deformation, then restore the original
  pose and time. For solver-driven chains, also run a minimal IK and pole-vector
  test.
- On an existing rig, verify that child world transforms, rest shape, weights,
  constraints, animation, and bind state remain unchanged except where the task
  explicitly required a change.

If evidence conflicts, stop and report the ambiguity instead of repeatedly
applying guessed orientations. Report the convention used, what changed, the
checks performed, and any remaining uncertainty. Keep orientation defects
separate from pivot-placement, solver, and skin-weight problems.

## Optional Frameworks

Use `detect_rig_frameworks` before relying on optional packages such as mGear,
AdvancedSkeleton, MGTools, Go Skinning, Skin Magic, SI Weight Editor, or
MetaHuman-style DNA tools. Built-in rigging tools remain the default path; optional
frameworks are only used when detection reports `available=true`.
