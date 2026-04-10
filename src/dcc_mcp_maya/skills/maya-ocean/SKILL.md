---
name: maya-ocean
description: Maya Ocean Shader — create ocean deformers, set wave attributes, manage ocean previews
dcc: maya
tags: [ocean, water, simulation, shader, vfx]
version: "1.0.0"
license: "MIT"
allowed-tools: ["Bash", "Read"]
depends: []
---
# maya-ocean

Maya Ocean skill. Provides actions for creating and managing Maya ocean shaders,
wave deformers, and ocean-related attributes.

## Scripts

- `create_ocean` — Create an ocean plane with oceanShader and oceanDeformer
- `list_oceans` — List all ocean deformer nodes in the scene
- `delete_ocean` — Delete an ocean deformer and related nodes
- `set_ocean_attribute` — Set wave height, scale, speed, or any ocean attribute
- `create_wake` — Create a wake effect attached to an ocean
