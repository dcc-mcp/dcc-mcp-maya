---
name: maya-skinning-utils
description: Maya skinning utilities — copy weights, normalize, mirror, prune, and query skin cluster data
dcc: maya
version: 1.0.0
tags:
- maya
- skinning
- skin-cluster
- weights
- rigging
search-hint: skin, weight, bind, copy weights, smooth
license: MIT
allowed-tools:
- Bash
- Read
depends: []
tools:
- name: copy_skin_weights
- name: mirror_skin_weights
- name: normalize_skin_weights
- name: prune_skin_weights
groups:
- name: rigging
  description: Rigging, deformation, and skinning tools
  default_active: false
  tools:
  - copy_skin_weights
  - mirror_skin_weights
  - normalize_skin_weights
  - prune_skin_weights
---
# maya-skinning-utils

Skin cluster weight management and utilities for Maya. Covers copying weights between meshes,
normalizing/pruning influences, mirroring weights, and querying per-vertex influence data.

## Scripts

- `copy_skin_weights` — Copy skin weights from a source mesh to a target mesh
- `normalize_skin_weights` — Normalize skin weights so they sum to 1.0 per vertex
- `mirror_skin_weights` — Mirror skin weights across an axis plane
- `prune_skin_weights` — Remove influences below a threshold and re-normalize
