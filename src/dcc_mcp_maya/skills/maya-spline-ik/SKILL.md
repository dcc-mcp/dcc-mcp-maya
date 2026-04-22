---
name: maya-spline-ik
description: Maya spline IK utilities — create and configure spline IK chains for spine and ribbon setups. Use when building flexible joint chains in rigs. Not for standard single-chain IK or full rig creation — use maya-rigging or maya-rig-utils for that.
license: MIT
allowed-tools: Bash Read
metadata:
  dcc-mcp:
    dcc: maya
    layer: domain
    version: 1.0.0
    tags:
    - maya
    - ik
    - spline
    - rigging
    - spine
    search-hint: spine rig, ribbon setup, flexible joint chain, spline IK
    depends: []
    tools: tools.yaml
    groups: groups.yaml
---
# maya-spline-ik

Spline IK handle creation and configuration tools for ribbon spines and tail rigs.
Covers ikSplineSolver handle creation, twist settings, and stretch setup.

## Scripts

- `create_spline_ik` — Create a spline IK handle between two joints using an existing or auto-generated curve
- `set_spline_ik_twist` — Configure advanced twist controls (world up type, up vectors) on a spline IK handle
- `add_stretch_to_spline_ik` — Add arc-length stretch so joints scale along the spine curve
- `list_spline_ik_handles` — List all ikSplineSolver handles in the scene
