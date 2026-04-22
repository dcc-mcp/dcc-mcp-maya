---
name: maya-camera-sequence
description: Maya camera sequencer — create, list, trim, and bake camera cuts for multi-shot timelines. Use when managing editorial shot cuts within Maya. Not for single camera setup or rendering — use maya-cameras or maya-render for that.
license: MIT
allowed-tools: Bash Read
metadata:
  dcc-mcp:
    dcc: maya
    layer: domain
    version: 1.0.0
    tags:
    - maya
    - camera
    - sequencer
    - shots
    - animation
    search-hint: shot cut, camera sequence, editorial timeline, multi-camera
    depends: []
    tools: tools.yaml
    groups: groups.yaml
---
# maya-camera-sequence

Camera Sequencer utilities for Maya. Manage multi-shot camera sequences using Maya's
built-in sequencer or shot nodes.

## Scripts

- `create_shot` — Create a Maya shot node and assign a camera for a frame range
- `list_shots` — List all shot nodes with their camera, start/end frame, and sequence order
- `set_shot_range` — Modify the start/end frame of an existing shot node
- `delete_shot` — Delete a shot node
