---
name: maya-spline-ik
description: "Maya spline IK utilities — create and configure spline IK chains for ribbon/spine rigs"
dcc: maya
version: "1.0.0"
tags: [maya, ik, spline, rigging, spine]
license: "MIT"
allowed-tools: ["Bash", "Read"]
depends: []
---

# maya-spline-ik

Spline IK handle creation and configuration tools for ribbon spines and tail rigs.
Covers ikSplineSolver handle creation, twist settings, and stretch setup.

## Scripts

- `create_spline_ik` — Create a spline IK handle between two joints using an existing or auto-generated curve
- `set_spline_ik_twist` — Configure advanced twist controls (world up type, up vectors) on a spline IK handle
- `add_stretch_to_spline_ik` — Add arc-length stretch so joints scale along the spine curve
- `list_spline_ik_handles` — List all ikSplineSolver handles in the scene
