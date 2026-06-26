---
name: maya-light-rig
description: |-
  Authoring stage — pre-configured lighting templates: three-point rigs,
  HDRI domes, individual lights, and rig-level intensity controls. Use when
  deploying a ready-made lighting setup or adding a typed light without falling
  back to raw Maya commands. Not for final render output — use maya-render for
  output settings.
license: MIT
allowed-tools: Bash Read
metadata:
  dcc-mcp:
    dcc: maya
    layer: domain
    stage: authoring
    version: 1.1.0
    tags:
    - maya
    - lighting
    - light-rig
    - three-point
    - hdri
    search-hint: |-
      lighting template, three point rig, key fill rim, HDRI dome,
      studio setup, environment light
    tools: tools.yaml
    groups: groups.yaml
---
# maya-light-rig (Authoring stage)

Standard lighting rigs (three-point, HDRI dome) and rig-level intensity
controls. Designed for fast scene illumination without manually wiring
light nodes. `create_light` always returns both the transform and shape to
avoid Maya 2022 command return-value traps such as `cmds.directionalLight()`
returning a shape node.

## Scripts

- `create_light` — Create one typed light and return transform + shape
- `create_three_point_rig` — Create a standard key/fill/rim three-point light rig
- `create_hdri_dome` — Create a skydome/environment light from an HDR image
- `list_light_rigs` — List all lights grouped under rig transform nodes
- `set_light_rig_intensity` — Scale intensity of all lights within a named rig
