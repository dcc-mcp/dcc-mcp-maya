---
name: maya-pipeline
description: Pipeline integration utilities for Maya scenes — metadata tagging, asset publishing, and project workspace setup. Use when managing assets through a production pipeline. Not for individual object creation, mesh editing, or rendering — use maya-primitives, maya-mesh-ops, or maya-render for that.
license: MIT
allowed-tools: Bash Read
metadata:
  dcc-mcp:
    dcc: maya
    layer: domain
    version: 1.0.0
    tags:
    - maya
    - pipeline
    - asset
    - publish
    - project
    search-hint: asset publish, production pipeline, metadata tagging, project workspace
    depends: []
    tools: tools.yaml
    groups: groups.yaml
---
# maya-pipeline

Provides pipeline-aware actions for asset publishing, project path management and scene metadata tagging.

## Scripts

- `set_project` — Set the Maya project workspace directory
- `publish_asset` — Export selected geometry to a versioned publish path (FBX or MA)
- `tag_asset_metadata` — Store pipeline metadata (asset_name, variant, version, step) on a node
- `get_asset_metadata` — Retrieve pipeline metadata attributes from a node
