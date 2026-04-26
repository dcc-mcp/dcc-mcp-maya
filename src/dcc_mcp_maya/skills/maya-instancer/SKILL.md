---
name: maya-instancer
description: Maya instancer utilities — create and configure particle instancers for object replication. Use when replicating geometry via particle systems. Not for MASH networks or manual duplication — use maya-mash or maya-scene for that.
license: MIT
allowed-tools: Bash Read
metadata:
  dcc-mcp:
    dcc: maya
    layer: domain
    version: 1.0.0
    tags:
    - maya
    - instancer
    - particles
    - scatter
    - motion-graphics
    search-hint: object replication, particle instancer, instance geometry
    depends: []
    tools: tools.yaml
    groups: groups.yaml
---
> **Deprecated (merge bucket):** This skill contains only thin \maya.cmds\ wrappers.
> Use \xecute_python\ with \maya-scripting/references/RECIPES.md#instancer\ instead.
> Will be removed in the next release.

# maya-instancer

Particle instancer tools for Maya. Allows scattering geometry across particle systems,
configuring per-instance attributes, and managing instancer nodes.

## Scripts

- `create_instancer` — Create a particle instancer node linking a particle system to instance geometry
- `add_instance_object` — Add an additional geometry object to an existing instancer
- `set_instancer_attribute` — Configure instancer per-particle attributes (rotation, scale, visibility)
- `list_instancers` — List all instancer nodes and their linked particle systems and geometry
