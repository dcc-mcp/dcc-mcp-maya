---
name: maya-cache
description: Maya geometry and simulation cache operations — Alembic, nCache, GPU cache
dcc: maya
tags: [cache, alembic, ncache, geometry, simulation]
version: "1.0.0"
license: "MIT"
allowed-tools: ["Bash", "Read"]
depends: []
---
# maya-cache

Maya cache skill. Provides actions for exporting and importing geometry caches,
Alembic archives, and nCache simulation data.

## Scripts

- `export_alembic` — Export selected objects to Alembic (.abc) format
- `import_alembic` — Import an Alembic (.abc) file into the scene
- `create_ncache` — Create an nCache for nCloth/nParticle simulations
- `list_caches` — List all cache nodes attached to scene objects
- `delete_cache` — Delete/detach a cache from an object
