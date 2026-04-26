---
name: maya-toon
description: Maya toon shading — create toon outlines, fill shaders, and cel-shading networks. Use when producing stylized non-photorealistic looks. Not for standard PBR materials or photoreal lighting — use maya-materials or maya-lighting for that.
license: MIT
allowed-tools: Bash Read
metadata:
  dcc-mcp:
    dcc: maya
    layer: domain
    version: 1.0.0
    tags:
    - maya
    - toon
    - shading
    - npr
    - stylized
    search-hint: stylized look, cel shading, toon outline, NPR
    depends: []
    tools: tools.yaml
    groups: groups.yaml
---
> **Deprecated (merge bucket):** This skill contains only thin \maya.cmds\ wrappers.
> Use \xecute_python\ with \maya-scripting/references/RECIPES.md#toon\ instead.
> Will be removed in the next release.

# maya-toon

Non-photorealistic (NPR) toon shading utilities for Maya. Creates outline strokes,
surface shaders, and ramp-based fill shaders for cel-shading and stylized renders.

## Scripts

- `add_toon_outline` — Add a pfxToon outline stroke to selected meshes
- `create_toon_shader` — Create a ramp-based surface shader for cel shading
- `set_outline_width` — Adjust the line width of an existing pfxToon node
- `list_toon_outlines` — List all pfxToon nodes in the scene with linked meshes
