---
name: maya-xform-utils
description: Maya transform utilities — freeze, reset, match, bake, and mirror transforms and pivots. Use when adjusting object positioning and orientation. Not for animation curves or rigging constraints — use maya-animation or maya-constraints for that.
license: MIT
allowed-tools: Bash Read
metadata:
  dcc-mcp:
    dcc: maya
    layer: domain
    version: 1.0.0
    tags:
    - maya
    - transform
    - xform
    - freeze
    - pivot
    search-hint: adjust transform, freeze pivot, align objects, bake transform
    depends: []
    tools: tools.yaml
---
# maya-xform-utils

Advanced transform operations for Maya objects. Provides freeze/reset transforms,
pivot management, match transforms between objects, and world-space bake utilities.

## Scripts

- `freeze_transforms` — Freeze translate/rotate/scale on one or more objects
- `reset_pivot` — Move pivot to object bounding-box center or world origin
- `match_transforms` — Match position/rotation/scale of one object to another
- `bake_transforms` — Bake world-space transforms to keyframes over a frame range
