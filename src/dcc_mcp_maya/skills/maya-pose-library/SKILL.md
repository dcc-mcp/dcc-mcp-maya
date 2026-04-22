---
name: maya-pose-library
description: Maya pose library — save, load, apply, and manage character poses as presets. Use when reusing character poses across scenes. Not for animation curves or rigging setup — use maya-animation or maya-rigging for that.
license: MIT
allowed-tools: Bash Read
metadata:
  dcc-mcp:
    dcc: maya
    layer: domain
    version: 1.0.0
    tags:
    - maya
    - animation
    - pose
    - library
    - rigging
    search-hint: save load pose, character pose preset, reuse pose
    depends: []
    tools: tools.yaml
    groups: groups.yaml
---
# maya-pose-library

Pose capture and application utilities for Maya. Saves attribute snapshots to JSON
files and restores them, enabling pose library workflows for character animation.

## Scripts

- `save_pose` — Save current attribute values of selected controls to a JSON pose file
- `load_pose` — Apply a saved pose JSON file to matching controls in the scene
- `list_poses` — List all saved pose files in a directory
- `mirror_pose` — Mirror pose by applying left/right attribute swapping convention
