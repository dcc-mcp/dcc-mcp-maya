---
name: maya-pipeline
description: "Pipeline integration utilities for Maya scenes: metadata, asset publishing and project setup"
dcc: maya
version: "1.0.0"
tags: [maya, pipeline, asset, publish, project]
search-hint: "pipeline, publish, export, import, workflow"
license: "MIT"
allowed-tools: ["Bash", "Read"]
depends: []
---

# maya-pipeline

Provides pipeline-aware actions for asset publishing, project path management and scene metadata tagging.

## Scripts

- `set_project` — Set the Maya project workspace directory
- `publish_asset` — Export selected geometry to a versioned publish path (FBX or MA)
- `tag_asset_metadata` — Store pipeline metadata (asset_name, variant, version, step) on a node
- `get_asset_metadata` — Retrieve pipeline metadata attributes from a node
