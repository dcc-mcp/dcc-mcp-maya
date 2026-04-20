---
name: maya-muscle
description: Maya Muscle system for secondary motion — create muscles, capsules, and skin simulation
dcc: maya
tags:
- muscle
- simulation
- secondary-motion
- cMuscle
- rig
search-hint: muscle, cMuscle, tissue, deformation
version: 1.0.0
license: MIT
allowed-tools:
- Bash
- Read
depends: []
tools:
- name: apply_muscle_skin
  idempotent_hint: true
- name: create_muscle_capsule
- name: list_muscles
  read_only_hint: true
  idempotent_hint: true
- name: set_muscle_attribute
  idempotent_hint: true
groups:
- name: rigging
  description: Rigging, deformation, and skinning tools
  default_active: false
  tools:
  - apply_muscle_skin
  - create_muscle_capsule
  - list_muscles
  - set_muscle_attribute
---
# maya-muscle

Maya Muscle skill. Provides actions for creating muscle objects (cMuscleObject),
adding capsule muscles between joints, listing muscle nodes, and adjusting simulation attributes.

## Scripts

- `create_muscle_capsule` — Create a cMuscleObject capsule between two joints
- `list_muscles` — List all cMuscleObject nodes in the scene
- `set_muscle_attribute` — Set a cMuscleObject simulation attribute (stiffness, jiggle, etc.)
- `apply_muscle_skin` — Apply cMuscleSystem deformer to a mesh
