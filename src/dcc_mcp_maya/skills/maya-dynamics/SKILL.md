---
name: maya-dynamics
description: |-
  Authoring stage - classic Maya dynamics primitives: rigid bodies,
  force fields, and field connections. Use for small simulation setup
  steps before baking with maya-animation. Not for keyframe editing
  (maya-animation), mesh modeling (maya-mesh-ops), or viewport output
  (maya-render).
license: MIT
allowed-tools: Bash Read
metadata:
  dcc-mcp:
    dcc: maya
    layer: domain
    stage: authoring
    version: 1.0.0
    tags:
    - maya
    - dynamics
    - rigid-body
    - physics
    - gravity
    - field
    search-hint: |-
      dynamics, rigid body, rigidBody, active body, passive body, gravity field,
      connect dynamic field, simulation setup, bounce, friction, mass
    tools: tools.yaml
    groups: groups.yaml
---
# maya-dynamics (Authoring stage)

Typed wrappers for Maya's classic dynamics setup commands. Keep this skill
focused on small graph mutations that agents otherwise tend to attempt through
`execute_python` with fragile command flags.

Use `maya-animation.bake_simulation` after the dynamic setup is working and
needs to be converted to keyframes for export.

## Scripts

- `list_dynamics` - List rigid bodies, dynamic fields, and rigid constraints
- `make_rigid_body` - Add active or passive rigid bodies to scene objects
- `set_rigid_body_properties` - Edit common rigid body physical properties
- `create_gravity_field` - Create a gravity field and optionally connect targets
- `connect_dynamic_field` - Connect or disconnect existing fields from dynamic targets
