---
name: maya-mocap
description: Motion capture data import, retargeting, and cleanup for Maya. Use when bringing external mocap data onto rigs. Not for keyframe animation or rigging — use maya-animation or maya-rigging for that.
license: MIT
allowed-tools: Bash Read
metadata:
  dcc-mcp:
    dcc: maya
    layer: domain
    version: 1.0.0
    tags:
    - maya
    - mocap
    - animation
    - retarget
    - hik
    - bvh
    search-hint: mocap retarget, motion capture import, cleanup retargeting
    depends: []
    tools: tools.yaml
    groups: groups.yaml
---
# maya-mocap

Motion capture skill for Maya. Provides actions for importing BVH/FBX mocap files,
mapping skeletons via HumanIK, baking motion onto rigs, and cleaning up imported data.

## Scripts

- `import_mocap` — Import a mocap file (BVH or FBX) and create the skeleton hierarchy
- `create_hik_definition` — Create a HumanIK character definition and map joints
- `bake_mocap_to_rig` — Bake HumanIK retargeted motion onto a rig skeleton
- `clean_mocap_keys` — Simplify/reduce keyframes on mocap curves using Maya's simplify
