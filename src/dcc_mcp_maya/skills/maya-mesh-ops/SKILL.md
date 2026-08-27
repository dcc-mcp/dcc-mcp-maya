---
name: maya-mesh-ops
description: |-
  Authoring stage — typed polygon construction and editing: loft, lathe,
  instance arrays, pivots, mirror, combine, separate, and cleanup. Use for
  creating or modifying polygon topology from explicit scene inputs.
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
    - loft
    - lathe
    - instances
    search-hint: |-
      edit mesh, modify polygons, loft sections, lathe profile, revolve curve,
      instance array, set pivot, mirror, combine, separate, cleanup, subdivide
    tools: tools.yaml
    groups: groups.yaml
    recipes: references/RECIPES.yaml
---
# maya-mesh-ops (Authoring stage)

Typed polygon construction and editing operations. `loft_sections` and
`lathe_profile` accept existing NURBS curves and require a polygon-mesh
readback. `array_instances` is capped at 128 objects and verifies every
instance transform. `set_pivot` reads back both Maya pivots. Primitive
creation remains in `maya-primitives`, while construction-history inspection
belongs to `maya-node-graph`.

Each tool declares `affinity: main` because every operation touches
`maya.cmds`; the dispatcher schedules them on Maya's UI thread via
`MayaUiDispatcher`.

The `modeling` group is `default_active: false`; load this skill and activate
that group only for authoring work. The existing `mirror_mesh` name remains
the canonical backwards-compatible mirror verb and now verifies that polygon
topology changed before returning success.

## Modeling recipes

The sibling `references/RECIPES.yaml` publishes four bounded Maya plans through
Core's `recipes__search`, `recipes__validate`, and `recipes__apply` tools. An
apply call returns validated inputs, ordered typed-tool steps, and an output
contract; execute those typed steps in order and validate the observed tool
result against the contract. Core does not substitute one step's Maya return
value into a later step, so recipes only chain steps whose identities come from
the validated inputs. `mirror_assembly` therefore mirrors one named mesh in
place and does not promise a preserved original or a separately named copy.
`auto_uv_for_export` is intentionally one mesh per application so every export
mesh must independently produce a positive UV count and digest.
