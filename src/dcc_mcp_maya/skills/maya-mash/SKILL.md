---
name: maya-mash
description: Maya MASH motion graphics network — create, modify, and query MASH networks for procedural distribution. Use when scattering or distributing objects procedurally. Not for standard particle effects or instancing — use maya-nparticles or maya-instancer for that.
license: MIT
allowed-tools: Bash Read
metadata:
  dcc-mcp:
    dcc: maya
    layer: domain
    version: 1.0.0
    tags:
    - maya
    - mash
    - motion-graphics
    - instancer
    - dynamics
    search-hint: procedural distribution, scatter objects, motion graphics MASH
    depends: []
    tools: tools.yaml
    groups: groups.yaml
---
# maya-mash

Maya MASH skill. Provides actions for creating and managing MASH networks for
motion graphics, instancing, and procedural animation.

## Scripts

- `create_network` — Create a MASH network for an object
- `list_networks` — List all MASH networks in the scene
- `delete_network` — Delete a MASH network
- `add_node` — Add a MASH node to an existing network
- `set_mash_attribute` — Set an attribute on a MASH node
