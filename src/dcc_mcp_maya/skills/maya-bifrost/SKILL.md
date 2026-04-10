---
name: maya-bifrost
description: Bifrost visual programming graph management for simulations and effects
dcc: maya
tags: [bifrost, simulation, vfx, graph]
version: "1.0.0"
license: "MIT"
allowed-tools: ["Bash", "Read"]
depends: []
---
# Maya Bifrost Skill

Provides Bifrost graph creation, compound management, port connection, and attribute control.

## Scripts

- `create_bifrost_graph` — Create a new Bifrost graph node in the scene
- `list_bifrost_graphs` — List all Bifrost graph nodes in the scene
- `add_bifrost_node` — Add a Bifrost compound/node to an existing graph
- `connect_bifrost_ports` — Connect output port to input port within a Bifrost graph
- `set_bifrost_property` — Set a property value on a Bifrost node
