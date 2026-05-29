---
name: maya-procedural-rig
description: |-
  Pipeline stage — typed, schema-validated procedural workflow that chains
  staged tools end to end: lay out spheres, shade them from a palette, build a
  radial joint skeleton, bind, keyframe an orbit/bounce/spin animation, capture
  a playblast, and export an interchange file. Use this instead of one big
  execute_python loop when you want validated parameters, structured results,
  and a reproducible stage-by-stage chain. For arbitrary modelling code drop
  into maya-scripting; for one-off primitives use maya-primitives.
license: MIT
allowed-tools: Bash Read
metadata:
  dcc-mcp:
    dcc: maya
    layer: domain
    stage: pipeline
    version: 1.0.0
    tags:
    - maya
    - procedural
    - workflow
    - rig
    - animation
    - playblast
    - export
    search-hint: |-
      procedural workflow, sphere layout, generate spheres, palette materials,
      auto rig joints, bind to joints, orbit animation, bounce spin keyframes,
      playblast preview, export fbx obj, staged pipeline, chain tools end to end,
      demo scene generator, motion graphics spheres
    tools: tools.yaml
    groups: groups.yaml
---
# maya-procedural-rig (Pipeline stage)

A typed, end-to-end procedural workflow. Each tool is a discrete, validated
stage that hands its results to the next one through structured context, so an
agent can build a complete animated, shaded, rigged demo scene and export it
**without** falling back to one large `execute_python` script (and losing input
validation, `ToolAnnotations`, and structured envelopes).

## The workflow chain

| Stage | Tool | Consumes | Produces |
|-------|------|----------|----------|
| 1. Layout | `create_sphere_layout` | — | `object_names` |
| 2. Shade | `assign_palette_materials` | `objects` | `assignments` |
| 3. Skeleton | `create_rig_joints` | `objects` | `root_joint`, `joints` |
| 4. Bind | `bind_objects_to_joints` | `objects`, `joints` | `bindings` |
| 5. Animate | `keyframe_orbit_animation` | `nodes` (joints) | frame range |
| 6. Preview | `create_playblast` | timeline | `output_path` |
| 7. Export | `export_scene_artifact` | scene / selection | `output_path` |

Each result carries a `prompt` pointing at the next stage, so the chain is
discoverable from any starting point.

## When to use this skill (vs alternatives)

| Goal | Use |
|------|-----|
| Generate a full animated/shaded sphere demo scene + playblast + export | **maya-procedural-rig** |
| Just create a few primitives | maya-primitives |
| Hand-author a complex rig | maya-rigging |
| Fine-grained animation curves | maya-animation |
| Arbitrary procedural code | maya-scripting + execute_python |

## Scripts

- `create_sphere_layout` — Distribute polygon spheres (sphere / grid / line)
- `assign_palette_materials` — One Lambert per object from a generated palette
- `create_rig_joints` — Root joint + per-object child joints
- `bind_objects_to_joints` — Constraint / parent binding in parallel order
- `keyframe_orbit_animation` — Orbit / bounce / spin keyframes over a range
- `create_playblast` — Capture a viewport preview to disk
- `export_scene_artifact` — Export the scene or selection (ma/mb/obj/fbx)
