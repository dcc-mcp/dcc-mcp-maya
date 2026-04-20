---
name: maya-rig-utils
description: Maya rig utilities — space switching, control curve shapes, rig connections, and attribute locking
dcc: maya
version: 1.0.0
tags:
- maya
- rigging
- controls
- space-switch
- attributes
search-hint: rig, utility, mirror, constraint, helper
license: MIT
allowed-tools:
- Bash
- Read
depends: []
tools:
- name: add_space_switch
- name: connect_attributes
- name: create_control_curve
- name: lock_hide_attributes
groups:
- name: rigging
  description: Rigging, deformation, and skinning tools
  default_active: false
  tools:
  - add_space_switch
  - connect_attributes
  - create_control_curve
  - lock_hide_attributes
---
# maya-rig-utils

Rig utility actions for Maya. Covers creating control curve shapes, locking/hiding
attributes, building space switch setups, and managing rig connections.

## Scripts

- `create_control_curve` — Create a nurbs control curve shape (circle, square, arrow, etc.)
- `lock_hide_attributes` — Lock and/or hide specified attributes on a node
- `add_space_switch` — Add space switch constraint with enum attribute and driven key
- `connect_attributes` — Connect one or more source attributes to destination attributes
