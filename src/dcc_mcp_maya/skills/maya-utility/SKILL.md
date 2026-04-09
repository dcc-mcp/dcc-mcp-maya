---
name: maya-utility
description: "Maya utility nodes and scene statistics"
dcc: maya
version: "1.0.0"
tags: [maya, utility, node, scene]
license: "MIT"
allowed-tools: ["Bash", "Read"]
depends: []
---

# maya-utility

Maya utility skill. Provides actions for creating utility/shading nodes and querying scene statistics.

## Scripts

- `create_utility_node` — Create any Maya utility or shading node by type
- `get_scene_statistics` — Query scene-level statistics: polygon counts, node counts and memory
