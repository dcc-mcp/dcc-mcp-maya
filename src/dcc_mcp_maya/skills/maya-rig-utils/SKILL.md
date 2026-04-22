---
name: maya-rig-utils
description: Maya rig utilities — space switching, control curve shapes, rig connections, and mirroring. Use when supporting and extending existing rigs. Not for full rig creation or animation — use maya-rigging or maya-animation for that.
license: MIT
allowed-tools: Bash Read
metadata:
  dcc-mcp:
    dcc: maya
    layer: domain
    version: 1.0.0
    tags:
    - maya
    - rigging
    - controls
    - space-switch
    - attributes
    search-hint: rig helper, space switch, control shape, mirror rig
    depends: []
    tools: tools.yaml
    groups: groups.yaml
---
# maya-rig-utils

Rig utility actions for Maya. Covers creating control curve shapes, locking/hiding
attributes, building space switch setups, and managing rig connections.

## Scripts

- `create_control_curve` — Create a nurbs control curve shape (circle, square, arrow, etc.)
- `lock_hide_attributes` — Lock and/or hide specified attributes on a node
- `add_space_switch` — Add space switch constraint with enum attribute and driven key
- `connect_attributes` — Connect one or more source attributes to destination attributes
