---
name: maya-paint-effects
description: Maya Paint Effects — create, attach, and manage stroke brushes and Paint Effects nodes. Use when painting procedural 2D/3D strokes. Not for texture painting or vertex color — use maya-texture-bake or maya-vertex-color for that.
license: MIT
allowed-tools: Bash Read
metadata:
  dcc-mcp:
    dcc: maya
    layer: domain
    version: 1.0.0
    tags:
    - maya
    - paint-effects
    - strokes
    - brushes
    - stylized
    search-hint: procedural stroke, paint brush, 2D 3D paint effects
    depends: []
    tools: tools.yaml
    groups: groups.yaml
---
> **Deprecated (merge bucket):** This skill contains only thin \maya.cmds\ wrappers.
> Use \xecute_python\ with \maya-scripting/references/RECIPES.md#paint-effects\ instead.
> Will be removed in the next release.

# maya-paint-effects

Maya Paint Effects utilities: create brush strokes, attach presets to NURBS/polygon surfaces,
list and delete existing strokes, and adjust global stroke attributes.

## Scripts

- `create_stroke` — Create a standalone Paint Effects stroke in world space
- `attach_stroke_to_surface` — Attach a Paint Effects preset to a NURBS or polygon surface
- `list_strokes` — List all Paint Effects stroke nodes in the scene
- `delete_stroke` — Delete one or all Paint Effects stroke nodes
