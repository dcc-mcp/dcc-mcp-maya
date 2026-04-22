---
name: maya-cache
description: Maya geometry cache — create, attach, list, and delete geometry caches. Use when baking deformation to disk for playback. Not for GPU cache optimization or render caching — use maya-gpu-cache or maya-render for that.
license: MIT
allowed-tools: Bash Read
metadata:
  dcc-mcp:
    dcc: maya
    layer: domain
    version: 1.0.0
    tags:
    - maya
    - cache
    - geometry
    - simulation
    search-hint: bake deformation, geometry cache, playback cache, deformation disk
    depends: []
    tools: tools.yaml
---
# maya-cache

Maya cache skill. Provides actions for baking geometry deformations to disk cache
files and attaching cached data back to meshes. Useful for preserving simulations
and speeding up playback.

## Scripts

- `create_geometry_cache` — Bake geometry deformations to a disk cache file
- `attach_geometry_cache` — Attach an existing cache file to a mesh
- `list_geometry_caches` — List cache nodes attached to a mesh
- `delete_geometry_cache` — Delete a geometry cache node and optionally its files
