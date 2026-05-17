---
name: maya-pipeline
description: |-
  Pipeline stage — production pipeline integration: project workspace
  setup, asset publishing, metadata tagging. Use when moving assets through
  a versioned pipeline. Not for primitive creation (maya-primitives), mesh
  editing (maya-mesh-ops), or rendering (maya-render).
license: MIT
allowed-tools: Bash Read
metadata:
  dcc-mcp:
    dcc: maya
    layer: domain
    stage: pipeline
    version: 1.1.0
    tags:
    - maya
    - pipeline
    - asset
    - publish
    - project
    - metadata
    search-hint: |-
      asset publish, production pipeline, metadata tagging, project workspace,
      versioned publish, set project, tag asset, get asset metadata
    depends:
    - maya-geometry
    tools: tools.yaml
    groups: groups.yaml
---
# maya-pipeline (Pipeline stage)

Project workspace, asset publishing, metadata tagging. Sits on top of
`maya-geometry` (declared in `depends`): publishing an asset involves
writing the geometry through Interchange tools and recording metadata
into the scene.

## Scripts

- `set_project` — Set the Maya project workspace directory
- `publish_asset` — Export selected geometry to a versioned publish path (FBX or MA)
- `tag_asset_metadata` — Store pipeline metadata (asset_name, variant, version, step) on a node
- `get_asset_metadata` — Retrieve pipeline metadata attributes from a node
