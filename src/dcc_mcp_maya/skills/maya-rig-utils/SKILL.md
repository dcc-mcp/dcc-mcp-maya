---
name: maya-rig-utils
description: "Maya rig utilities — space switching, control curve shapes, rig connections, and attribute locking"
dcc: maya
version: "1.0.0"
tags: [maya, rigging, controls, space-switch, attributes]
license: "MIT"
allowed-tools: ["Bash", "Read"]
depends: []
---

# maya-rig-utils

Rig utility actions for Maya. Covers creating control curve shapes, locking/hiding
attributes, building space switch setups, and managing rig connections.

## Scripts

- `create_control_curve` — Create a nurbs control curve shape (circle, square, arrow, etc.)
- `lock_hide_attributes` — Lock and/or hide specified attributes on a node
- `add_space_switch` — Add space switch constraint with enum attribute and driven key
- `connect_attributes` — Connect one or more source attributes to destination attributes
