---
name: maya-cache
<<<<<<< HEAD
description: "Maya geometry cache node listing and management"
=======
description: "Maya geometry cache — create, attach, list and delete geometry caches for mesh deformations"
>>>>>>> origin/main
dcc: maya
version: "1.0.0"
tags: [maya, cache, geometry, simulation]
license: "MIT"
allowed-tools: ["Bash", "Read"]
depends: []
---

# maya-cache

<<<<<<< HEAD
Maya cache skill. Provides actions for querying geometry cache nodes in Maya.

## Scripts

- `list_geometry_caches` — List cache nodes attached to a mesh (or all cacheFile nodes if no mesh specified)
=======
Maya cache skill. Provides actions for baking geometry deformations to disk cache
files and attaching cached data back to meshes. Useful for preserving simulations
and speeding up playback.

## Scripts

- `create_geometry_cache` — Bake geometry deformations to a disk cache file
- `attach_geometry_cache` — Attach an existing cache file to a mesh
- `list_geometry_caches` — List cache nodes attached to a mesh
- `delete_geometry_cache` — Delete a geometry cache node and optionally its files
>>>>>>> origin/main
