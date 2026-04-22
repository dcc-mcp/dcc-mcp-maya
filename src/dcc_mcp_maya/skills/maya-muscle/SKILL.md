---
name: maya-muscle
description: Maya Muscle system — create muscles, capsules, and tissue deformers for secondary motion. Use when adding anatomical deformation to characters. Not for standard skin clusters or blend shapes — use maya-skinning-utils or maya-blend-shape-utils for that.
license: MIT
allowed-tools: Bash Read
metadata:
  dcc-mcp:
    dcc: maya
    layer: domain
    version: 1.0.0
    tags:
    - maya
    - muscle
    - simulation
    - secondary-motion
    - rig
    search-hint: anatomical deformation, muscle tissue, secondary motion
    depends: []
    tools: tools.yaml
    groups: groups.yaml
---
# maya-muscle

Maya Muscle skill. Provides actions for creating muscle objects (cMuscleObject),
adding capsule muscles between joints, listing muscle nodes, and adjusting simulation attributes.

## Scripts

- `create_muscle_capsule` — Create a cMuscleObject capsule between two joints
- `list_muscles` — List all cMuscleObject nodes in the scene
- `set_muscle_attribute` — Set a cMuscleObject simulation attribute (stiffness, jiggle, etc.)
- `apply_muscle_skin` — Apply cMuscleSystem deformer to a mesh
