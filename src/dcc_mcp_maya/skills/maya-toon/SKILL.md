---
name: maya-toon
description: Maya Toon — create toon outlines, assign toon shaders, set line attributes
dcc: maya
tags: [toon, outline, shader, stylized, rendering]
version: "1.0.0"
license: "MIT"
allowed-tools: ["Bash", "Read"]
depends: []
---
# maya-toon

Maya Toon skill. Provides actions for creating toon outline strokes, assigning
toon shaders, listing toon nodes, and configuring line thickness and color.

## Scripts

- `create_toon_outline` — Add a toon outline stroke to selected or named objects
- `list_toon_lines` — List all pfxToon nodes in the scene
- `delete_toon_line` — Delete a pfxToon outline node
- `set_toon_attribute` — Set line width, color, or any pfxToon attribute
- `assign_toon_shader` — Create and assign a surfaceShader-based toon material
