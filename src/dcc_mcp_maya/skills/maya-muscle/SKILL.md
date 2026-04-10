---
name: maya-muscle
description: Maya Muscle system — create capsules/muscles, attach to joints, set muscle weights
dcc: maya
tags: [muscle, rigging, simulation, deformation]
version: "1.0.0"
license: "MIT"
allowed-tools: ["Bash", "Read"]
depends: []
---
# maya-muscle

Maya Muscle skill. Provides actions for creating and configuring Maya Muscle capsules,
attaching them to skeleton joints, querying muscle info, and setting muscle tension weights.

## Scripts

- `create_muscle_capsule` — Create a cMuscleObject capsule between two joints
- `list_muscles` — List all cMuscleObject nodes in the scene
- `delete_muscle` — Delete a muscle capsule and its driver nodes
- `set_muscle_attribute` — Set an attribute on a muscle capsule (e.g. rest, squash)
- `attach_muscle_to_skin` — Attach a muscle to a cMuscleSystem skin deformer
