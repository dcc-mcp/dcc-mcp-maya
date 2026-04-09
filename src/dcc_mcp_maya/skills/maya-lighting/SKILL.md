---
name: maya-lighting
description: "Maya scene lighting — create, modify and query light nodes"
dcc: maya
version: "1.0.0"
tags: [maya, lighting, light, render]
license: "MIT"
allowed-tools: ["Bash", "Read"]
depends: []
---

# maya-lighting

Maya lighting skill. Provides actions for creating lights (directional, point,
spot, area, ambient), adjusting light attributes, and listing all scene lights.

## Scripts

- `create_light` — Create a Maya light (directional, point, spot, area, ambient)
- `set_light_attribute` — Set a named attribute on a light node (intensity, color, shadows)
- `list_lights` — List all lights in the current scene with type and intensity
