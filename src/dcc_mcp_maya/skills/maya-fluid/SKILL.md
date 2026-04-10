---
name: maya-fluid
description: Maya Fluid Effects — create fluid containers, list/delete, set attributes, add emitters
dcc: maya
tags: [fluid, dynamics, simulation, vfx]
version: "1.0.0"
license: "MIT"
allowed-tools: ["Bash", "Read"]
depends: []
---
# maya-fluid

Maya Fluid Effects skill. Provides actions for creating and managing Maya fluid containers
(3D/2D), listing fluid nodes, setting resolution and attribute values, and attaching
fluid emitters.

## Scripts

- `create_fluid_container` — Create a 3D or 2D fluid container
- `list_fluid_containers` — List all fluid containers in the scene
- `delete_fluid_container` — Delete a fluid container and its emitters
- `set_fluid_attribute` — Set an attribute on a fluid container
- `add_fluid_emitter` — Add an emitter to an existing fluid container
