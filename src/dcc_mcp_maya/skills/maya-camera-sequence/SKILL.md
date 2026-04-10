---
name: maya-camera-sequence
description: "Maya camera sequencer — create, list, trim, and bake camera cuts for multi-shot sequences"
dcc: maya
version: "1.0.0"
tags: [maya, camera, sequencer, shots, animation]
license: "MIT"
allowed-tools: ["Bash", "Read"]
depends: []
---

# maya-camera-sequence

Camera Sequencer utilities for Maya. Manage multi-shot camera sequences using Maya's
built-in sequencer or shot nodes.

## Scripts

- `create_shot` — Create a Maya shot node and assign a camera for a frame range
- `list_shots` — List all shot nodes with their camera, start/end frame, and sequence order
- `set_shot_range` — Modify the start/end frame of an existing shot node
- `delete_shot` — Delete a shot node
