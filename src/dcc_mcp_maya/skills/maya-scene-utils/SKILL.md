---
name: maya-scene-utils
description: Maya scene helper utilities — pivot alignment, annotation, color override, and locator creation. Use when adding helper objects and visual cues to a scene. Not for modeling or rendering — use maya-mesh-ops or maya-render for that.
license: MIT
allowed-tools: Bash Read
metadata:
  dcc-mcp:
    dcc: maya
    layer: domain
    version: 1.0.0
    tags:
    - maya
    - scene
    - utility
    - display
    - viewport
    search-hint: scene helper, locator, annotation, color override, alignment
    depends: []
    tools: tools.yaml
    groups: groups.yaml
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
