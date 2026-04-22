---
name: maya-paint-effects
description: Maya Paint Effects — create, attach, and manage stroke brushes and Paint
  Effects presets on surfaces
license: MIT
allowed-tools: Bash Read
metadata:
  dcc-mcp:
    dcc: maya
    version: 1.0.0
    tags:
    - maya
    - paint-effects
    - strokes
    - brushes
    - stylized
    search-hint: paint effects, stroke, brush, 3d paint
    depends: []
    tools: tools.yaml
    groups: groups.yaml
---
# maya-paint-effects

Maya Paint Effects utilities: create brush strokes, attach presets to NURBS/polygon surfaces,
list and delete existing strokes, and adjust global stroke attributes.

## Scripts

- `create_stroke` — Create a standalone Paint Effects stroke in world space
- `attach_stroke_to_surface` — Attach a Paint Effects preset to a NURBS or polygon surface
- `list_strokes` — List all Paint Effects stroke nodes in the scene
- `delete_stroke` — Delete one or all Paint Effects stroke nodes
