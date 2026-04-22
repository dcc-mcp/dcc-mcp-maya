---
name: maya-color-grading
description: Maya color management — query and set color space, apply LUTs and color correction. Use when managing color pipeline and look consistency. Not for material creation or lighting — use maya-materials or maya-lighting for that.
license: MIT
allowed-tools: Bash Read
metadata:
  dcc-mcp:
    dcc: maya
    layer: domain
    version: 1.0.0
    tags:
    - maya
    - color
    - color-management
    - aces
    - rendering
    search-hint: color space, LUT, color pipeline, look consistency
    depends: []
    tools: tools.yaml
    groups: groups.yaml
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
