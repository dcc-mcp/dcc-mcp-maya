---
name: maya-dynamics
description: |-
  Authoring stage - Maya dynamics: classic rigid bodies and force fields plus
  the Nucleus family (nCloth, passive colliders, Nucleus constraints, the
  nucleus solver) and nCache write/delete. Use for simulation setup steps
  before baking with maya-animation. Not for particle systems
  (maya-particles), Bifrost graphs (maya-bifrost), keyframe editing
  (maya-animation), mesh modeling (maya-mesh-ops), or viewport output
  (maya-render).
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
    - dynamics
    - nucleus
    - ncloth
    - nrigid
    - collider
    - constraint
    - rigid-body
    - physics
    - gravity
    - field
    - ncache
    search-hint: |-
      dynamics, rigid body, rigidBody, active body, passive body, gravity field,
      connect dynamic field, simulation setup, bounce, friction, mass,
      nCloth, nRigid, collider, passive collision object, nucleus solver,
      nConstraint, transform constraint, weld, force field, substeps,
      space scale, dynamic field, air field, drag field, turbulence field,
      vortex field, volume axis field, newton field, radial field,
      nCache, geometry cache, cacheFile, write cache, delete cache
    tools: tools.yaml
    groups: groups.yaml
---
# maya-dynamics (Authoring stage)

Typed wrappers for Maya's classic dynamics and Nucleus simulation commands.
Keep this skill focused on small graph mutations that agents otherwise tend to
attempt through `execute_python` with fragile command flags.

Use `maya-animation.bake_simulation` after the simulation is working and needs
to be converted to keyframes for export. Use `maya-particles` when the effect
is particle-driven rather than cloth-driven.

## Tool groups

| Group | Activated by | Contents |
|-------|--------------|----------|
| `dynamics` | `activate_group("dynamics")` | Classic rigid bodies and field connections |
| `nucleus` | `activate_group("nucleus")` | nCloth, nRigid colliders, Nucleus constraints, solver |
| `fields` | `activate_group("fields")` | The full dynamic field family |
| `constraints` | `activate_group("constraints")` | Classic rigid-body constraints |
| `cache` | `activate_group("cache")` | nCache write and delete |

## Cloth workflow

1. `make_rigid_body` for classic rigid-body work, or `create_ncloth` for cloth.
2. `create_nrigid` on any mesh the cloth should collide with.
3. `create_nconstraint` to pin cloth to a driver (transform, weld, force field…).
4. `create_nucleus` / `set_nucleus_properties` to tune gravity, wind, substeps
   and `space_scale` — `space_scale` is the single most common cause of a
   simulation that looks "too slow" or "exploding".
5. `create_dynamic_field` for forces, `set_field_properties` to refine them.
6. `create_ncache` once the motion is approved; `delete_ncache` to iterate.

## Scripts

- `connect_dynamic_field` - Connect or disconnect an existing dynamic field from dynamic targets
- `create_dynamic_field` - Create any Maya dynamic field and optionally connect it to targets
- `create_gravity_field` - Create a gravity field and optionally connect targets
- `create_ncache` - Write geometry / nCache files for Nucleus or deformable output
- `create_ncloth` - Convert polygon meshes into Nucleus nCloth objects
- `create_nconstraint` - Create a Nucleus constraint from driven nodes to an optional driver
- `create_nrigid` - Turn meshes into passive Nucleus collision objects
- `create_nucleus` - Create a standalone Nucleus solver node
- `create_rigid_constraint` - Constrain classic rigid bodies (nail, pin, hinge, spring, barrier)
- `delete_ncache` - Detach and delete cacheFile nodes, optionally deleting the files
- `list_dynamics` - List rigid bodies, dynamic fields, and rigid constraints
- `make_rigid_body` - Add active or passive rigid bodies to scene objects
- `set_field_properties` - Edit attributes on existing dynamic field nodes
- `set_ncloth_properties` - Edit physical properties on nCloth / nRigid shapes
- `set_nucleus_properties` - Edit global Nucleus solver settings
- `set_rigid_body_properties` - Edit common rigid body physical properties
