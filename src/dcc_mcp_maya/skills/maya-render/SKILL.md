---
name: maya-render
description: "Maya render settings and viewport capture"
dcc: maya
version: "1.0.0"
tags: [maya, render, playblast, settings]
license: "MIT"
allowed-tools: ["Bash", "Read"]
depends: []
tools:
  - name: set_render_settings
    description: "Set render parameters (resolution, frame range, renderer, image format)"
    source_file: scripts/set_render_settings.py
    read_only: false
    destructive: false
    idempotent: true
  - name: get_render_settings
    description: "Query current render settings"
    source_file: scripts/get_render_settings.py
    read_only: true
    destructive: false
    idempotent: true
  - name: playblast
    description: "Capture a viewport screenshot as a base64-encoded PNG"
    source_file: scripts/playblast.py
    read_only: true
    destructive: false
    idempotent: false
---

# maya-render

Maya render skill. Provides actions for managing render settings and capturing
viewport images.

## Scripts

- `set_render_settings` — Set render parameters (resolution, frame range, renderer, image format)
- `get_render_settings` — Query current render settings
- `playblast` — Capture a viewport screenshot as a base64-encoded PNG
