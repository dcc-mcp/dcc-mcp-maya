---
name: maya-skinning-utils
description: Maya skinning utilities — copy weights, normalize, mirror, prune, and smooth skin weights. Use when refining character skin deformation. Not for joint creation or blend shapes — use maya-rigging or maya-blend-shape-utils for that.
license: MIT
allowed-tools: Bash Read
metadata:
  dcc-mcp:
    dcc: maya
    layer: domain
    version: 1.0.0
    tags:
    - maya
    - skinning
    - skin-cluster
    - weights
    - rigging
    search-hint: refine skin weights, copy mirror weights, smooth deformation
    depends: []
    tools: tools.yaml
    groups: groups.yaml
---
# maya-skinning-utils

Skin cluster weight management and utilities for Maya. Covers copying weights between meshes,
normalizing/pruning influences, mirroring weights, and querying per-vertex influence data.

## Scripts

- `copy_skin_weights` — Copy skin weights from a source mesh to a target mesh
- `normalize_skin_weights` — Normalize skin weights so they sum to 1.0 per vertex
- `mirror_skin_weights` — Mirror skin weights across an axis plane
- `prune_skin_weights` — Remove influences below a threshold and re-normalize
