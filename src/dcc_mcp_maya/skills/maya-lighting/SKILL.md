---
name: maya-lighting
description: Maya scene lighting — create, modify, and query directional, point, spot, area, and ambient lights. Use when setting up illumination for a scene. Not for HDRI environments or toon shading — use maya-hdri or maya-toon for that.
license: MIT
allowed-tools: Bash Read
metadata:
  dcc-mcp:
    dcc: maya
    layer: domain
    version: 1.0.0
    tags:
    - maya
    - lighting
    - light
    - render
    search-hint: scene illumination, light setup, directional point spot light
    depends: []
    tools: tools.yaml
    groups: groups.yaml
---
# maya-lighting

Maya lighting skill. Provides actions for creating lights (directional, point,
spot, area, ambient), adjusting light attributes, and listing all scene lights.

## Scripts

- `create_light` — Create a Maya light (directional, point, spot, area, ambient)
- `set_light_attribute` — Set a named attribute on a light node (intensity, color, shadows)
- `list_lights` — List all lights in the current scene with type and intensity
