---
name: maya-paint-effects
description: Maya Paint Effects — create strokes, convert to polygons, set brush attributes
dcc: maya
tags: [paint-effects, brush, stroke, stylized, vfx]
version: "1.0.0"
license: "MIT"
allowed-tools: ["Bash", "Read"]
depends: []
---
# maya-paint-effects

Maya Paint Effects skill. Provides actions for creating Paint Effects strokes,
converting strokes to polygons, listing brush nodes, and setting brush attributes.

## Scripts

- `create_stroke` — Create a Paint Effects stroke on a mesh or at world coordinates
- `list_strokes` — List all stroke nodes in the scene
- `delete_stroke` — Delete a Paint Effects stroke node
- `set_brush_attribute` — Set brush scale, color, or any stroke attribute
- `convert_stroke_to_poly` — Convert a Paint Effects stroke to polygon geometry
