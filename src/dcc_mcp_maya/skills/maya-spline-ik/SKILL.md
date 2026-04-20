---
name: maya-spline-ik
description: Maya spline IK utilities — create and configure spline IK chains for ribbon/spine rigs
dcc: maya
version: 1.0.0
tags:
- maya
- ik
- spline
- rigging
- spine
search-hint: spline IK, curve, ribbon, spine
license: MIT
allowed-tools:
- Bash
- Read
depends: []
tools:
- name: add_stretch_to_spline_ik
- name: create_spline_ik
- name: list_spline_ik_handles
  read_only_hint: true
  idempotent_hint: true
- name: set_spline_ik_twist
  idempotent_hint: true
groups:
- name: rigging
  description: Rigging, deformation, and skinning tools
  default_active: false
  tools:
  - add_stretch_to_spline_ik
  - create_spline_ik
  - list_spline_ik_handles
  - set_spline_ik_twist
---
# maya-spline-ik

Spline IK handle creation and configuration tools for ribbon spines and tail rigs.
Covers ikSplineSolver handle creation, twist settings, and stretch setup.

## Scripts

- `create_spline_ik` — Create a spline IK handle between two joints using an existing or auto-generated curve
- `set_spline_ik_twist` — Configure advanced twist controls (world up type, up vectors) on a spline IK handle
- `add_stretch_to_spline_ik` — Add arc-length stretch so joints scale along the spine curve
- `list_spline_ik_handles` — List all ikSplineSolver handles in the scene
