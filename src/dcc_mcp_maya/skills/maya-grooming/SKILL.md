---
name: maya-grooming
description: Maya XGen interactive grooming — create, modify and export groom splines on meshes
dcc: maya
tags: [grooming, xgen, hair, fur, splines]
version: "1.0.0"
license: "MIT"
allowed-tools: ["Bash", "Read"]
depends: []
---
# maya-grooming

Maya interactive grooming skill using the XGen Interactive Groom API (`xgenm.igroom`).
Provides actions for creating groom descriptions, listing/deleting groomables, converting
splines to curves, and exporting/importing groom caches.

## Scripts

- `create_groom` — Create an XGen interactive groom description on a mesh
- `list_groomables` — List all interactive groom shapes in the scene
- `delete_groom` — Delete a groom description and its node
- `convert_groom_to_curves` — Convert groom splines to Maya NURBS curves
- `export_groom_cache` — Export an interactive groom cache to disk
