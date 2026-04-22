---
name: maya-light-rig
description: Maya light rig utilities — create standard three-point lighting rigs and HDRI dome setups. Use when deploying pre-configured lighting templates. Not for individual light creation or color grading — use maya-lighting or maya-color-grading for that.
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
    - light-rig
    - three-point
    - hdri
    search-hint: lighting template, three-point rig, studio setup, dome rig
    depends: []
    tools: tools.yaml
    groups: groups.yaml
---
# maya-light-rig

Light rig creation and management for Maya. Provides standard lighting setups
such as three-point rigs and HDRI dome lights for rapid scene illumination.

## Scripts

- `create_three_point_rig` — Create a standard key/fill/rim three-point light rig
- `create_hdri_dome` — Create a skydome/environment light from an HDR image
- `list_light_rigs` — List all lights grouped under rig transform nodes
- `set_light_rig_intensity` — Scale intensity of all lights within a named rig
