---
name: maya-mocap
description: Motion capture data import, retargeting and cleanup for Maya
dcc: maya
tags:
- mocap
- animation
- retarget
- hik
- bvh
search-hint: mocap, motion capture, retarget, fbx
version: 1.0.0
license: MIT
allowed-tools:
- Bash
- Read
depends: []
tools:
- name: bake_mocap_to_rig
- name: clean_mocap_keys
- name: create_hik_definition
- name: import_mocap
groups:
- name: animation
  description: Animation, constraints, and motion capture tools
  default_active: false
  tools:
  - bake_mocap_to_rig
  - clean_mocap_keys
  - create_hik_definition
  - import_mocap
---
# maya-mocap

Motion capture skill for Maya. Provides actions for importing BVH/FBX mocap files,
mapping skeletons via HumanIK, baking motion onto rigs, and cleaning up imported data.

## Scripts

- `import_mocap` — Import a mocap file (BVH or FBX) and create the skeleton hierarchy
- `create_hik_definition` — Create a HumanIK character definition and map joints
- `bake_mocap_to_rig` — Bake HumanIK retargeted motion onto a rig skeleton
- `clean_mocap_keys` — Simplify/reduce keyframes on mocap curves using Maya's simplify
