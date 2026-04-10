---
name: maya-color-grading
description: "Maya color management — query and set color space, apply color correction nodes to render settings"
dcc: maya
version: "1.0.0"
tags: [maya, color, color-management, aces, rendering]
license: "MIT"
allowed-tools: ["Bash", "Read"]
depends: []
---

# maya-color-grading

Maya color grading skill. Provides actions for managing Maya's color management
settings, including querying the active color space configuration, applying
gamma correction, and managing ACES/OCIO color pipelines.

## Scripts

- `get_color_management_info` — Query the current color management configuration
- `set_rendering_space` — Set the scene's rendering color space
- `set_view_transform` — Set the viewport color transform (view LUT)
- `apply_gamma_correction` — Apply a gamma correction node to a texture
