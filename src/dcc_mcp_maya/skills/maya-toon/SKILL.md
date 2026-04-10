---
name: maya-toon
description: "Maya toon shading — create toon outlines, fill shaders, and cel-shading looks using Maya's built-in toon system"
dcc: maya
version: "1.0.0"
tags: [maya, toon, shading, npr, stylized]
license: "MIT"
allowed-tools: ["Bash", "Read"]
depends: []
---

# maya-toon

Non-photorealistic (NPR) toon shading utilities for Maya. Creates outline strokes,
surface shaders, and ramp-based fill shaders for cel-shading and stylized renders.

## Scripts

- `add_toon_outline` — Add a pfxToon outline stroke to selected meshes
- `create_toon_shader` — Create a ramp-based surface shader for cel shading
- `set_outline_width` — Adjust the line width of an existing pfxToon node
- `list_toon_outlines` — List all pfxToon nodes in the scene with linked meshes
