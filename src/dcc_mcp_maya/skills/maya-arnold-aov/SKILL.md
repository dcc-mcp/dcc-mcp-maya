---
name: maya-arnold-aov
description: Arnold AOV management for multi-pass rendering — configure beauty, lighting, and custom Arbitrary Output Variables. Use when working with Arnold-specific render outputs. Not for standard Maya render passes or light setup — use maya-render-passes or maya-lighting for that.
license: MIT
allowed-tools: Bash Read
metadata:
  dcc-mcp:
    dcc: maya
    layer: domain
    version: 1.0.0
    tags:
    - maya
    - arnold
    - aov
    - render
    - passes
    search-hint: Arnold output, AOV configuration, multi-pass Arnold
    depends: []
    tools: tools.yaml
    groups: groups.yaml
---
# Maya Arnold AOV Skill

Provides Arnold AOV creation, listing, deletion, and attribute management.
Supports standard AOV types (beauty, diffuse, specular, Z, N, P, etc.) and custom AOVs.

## Scripts

- `add_aov` — Add a new Arnold AOV to the render settings
- `list_aovs` — List all existing Arnold AOVs
- `delete_aov` — Delete an Arnold AOV by name
- `set_aov_attribute` — Set an attribute on an Arnold AOV node
- `enable_aov` — Enable or disable an Arnold AOV
