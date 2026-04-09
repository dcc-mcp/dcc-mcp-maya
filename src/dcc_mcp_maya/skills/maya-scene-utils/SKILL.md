---
name: maya-scene-utils
description: "Maya scene utilities — pivot, alignment, annotation, color override and viewport shading"
dcc: maya
version: "1.0.0"
tags: [maya, scene, utility, display, viewport]
license: "MIT"
allowed-tools: ["Bash", "Read"]
depends: []
---

# maya-scene-utils

Maya scene utilities skill. Provides actions for setting pivots, aligning objects, creating annotations, setting object colors, toggling GPU override, managing shading modes, and creating polygon text.

## Scripts

- `set_pivot` — Set the rotate and/or scale pivot of a Maya object
- `align_objects` — Align a list of objects along a given world-space axis
- `create_annotation` — Create a Maya annotation node attached to an object
- `set_object_color` — Set the wireframe color of a Maya object by index
- `toggle_gpu_override` — Toggle the GPU override display mode on a polygon mesh
- `set_shading_mode` — Set the viewport shading mode for the active or specified panel
- `create_polygon_text` — Create a 3D polygon text object in the scene
