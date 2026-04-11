---
name: maya-muscle
description: Maya Muscle system for secondary motion — create muscles, capsules, and skin simulation
dcc: maya
tags: [muscle, simulation, secondary-motion, cMuscle, rig]
version: "1.0.0"
license: "MIT"
allowed-tools: ["Bash", "Read"]
depends: []
---

# maya-muscle

Maya Muscle skill. Provides actions for creating muscle objects (cMuscleObject),
adding capsule muscles between joints, listing muscle nodes, and adjusting simulation attributes.

## Scripts

- `create_muscle_capsule` — Create a cMuscleObject capsule between two joints
- `list_muscles` — List all cMuscleObject nodes in the scene
- `set_muscle_attribute` — Set a cMuscleObject simulation attribute (stiffness, jiggle, etc.)
- `apply_muscle_skin` — Apply cMuscleSystem deformer to a mesh
