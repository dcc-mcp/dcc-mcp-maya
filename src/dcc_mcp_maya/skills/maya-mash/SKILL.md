---
name: maya-mash
description: Maya MASH motion graphics network — create, modify and query MASH networks
license: MIT
allowed-tools: Bash Read
metadata:
  dcc-mcp:
    dcc: maya
    version: 1.0.0
    tags:
    - maya
    - mash
    - motion-graphics
    - instancer
    - dynamics
    search-hint: mash, motion graphics, distribute, scatter
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
