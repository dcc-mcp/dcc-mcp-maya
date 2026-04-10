---
name: maya-xform-utils
description: "Maya transform utilities — freeze, reset, match, bake, and mirror transforms"
dcc: maya
version: "1.0.0"
tags: [maya, transform, xform, freeze, pivot]
license: "MIT"
allowed-tools: ["Bash", "Read"]
depends: []
---

# maya-xform-utils

Advanced transform operations for Maya objects. Provides freeze/reset transforms,
pivot management, match transforms between objects, and world-space bake utilities.

## Scripts

- `freeze_transforms` — Freeze translate/rotate/scale on one or more objects
- `reset_pivot` — Move pivot to object bounding-box center or world origin
- `match_transforms` — Match position/rotation/scale of one object to another
- `bake_transforms` — Bake world-space transforms to keyframes over a frame range
