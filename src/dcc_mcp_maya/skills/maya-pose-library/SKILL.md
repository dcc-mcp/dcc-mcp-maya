---
name: maya-pose-library
description: |-
  Authoring stage — save / load / mirror character poses as JSON presets.
  Use for reusable pose libraries on rigged characters. Not for keyframe
  animation (maya-animation) or rigging setup (maya-rigging).
license: MIT
allowed-tools: Bash Read
metadata:
  dcc-mcp:
    dcc: maya
    layer: domain
    stage: authoring
    version: 1.1.0
    tags:
    - maya
    - animation
    - pose
    - library
    - rigging
    search-hint: |-
      save pose, load pose, mirror pose, character pose preset, pose library,
      pose JSON, reuse pose
    tools: tools.yaml
    groups: groups.yaml
---
# maya-pose-library (Authoring stage)

Pose capture and reapplication for character animation. Saves
attribute snapshots to JSON files and restores them, with an explicit
`mirror_pose` for left/right swapping conventions.

## Scripts

- `save_pose` — Save current attribute values of selected controls to a JSON pose file
- `load_pose` — Apply a saved pose JSON file to matching controls in the scene
- `list_poses` — List all saved pose files in a directory
- `mirror_pose` — Mirror pose by applying left/right attribute swapping convention
