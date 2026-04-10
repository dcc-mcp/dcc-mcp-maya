---
name: maya-gpu-cache
description: "Maya GPU cache utilities — export, import, and manage gpuCache nodes for viewport performance"
dcc: maya
version: "1.0.0"
tags: [maya, gpu-cache, alembic, viewport, performance]
license: "MIT"
allowed-tools: ["Bash", "Read"]
depends: []
---

# maya-gpu-cache

GPU cache (Alembic-based viewport proxy) management for Maya.
Speeds up viewport playback by replacing complex geometry with optimised GPU cache nodes.

## Scripts

- `export_gpu_cache` — Export selected objects to a GPU cache (.abc) file via gpuCache plugin
- `import_gpu_cache` — Import a GPU cache file and create a gpuCache node in the scene
- `list_gpu_caches` — List all gpuCache nodes with their file paths and frame ranges
- `refresh_gpu_cache` — Force a GPU cache node to reload its file from disk
