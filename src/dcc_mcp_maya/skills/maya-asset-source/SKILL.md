---
name: maya-asset-source
description: |-
  Pipeline stage — asset discovery and resolution. Search local asset
  libraries, resolve paths to structured AssetDescriptor records, and
  surface candidate assets for downstream import. Use before
  maya-import-to-scene to locate what to import.
license: MIT
allowed-tools: Bash Read
metadata:
  dcc-mcp:
    dcc: maya
    layer: domain
    stage: pipeline
    version: 1.0.0
    tags:
    - maya
    - asset
    - source
    - library
    - search
    - resolve
    - pipeline
    search-hint: |-
      search assets, find assets, asset library, resolve asset path,
      AssetDescriptor, asset discovery, FBX library, OBJ library,
      USD library, locate asset, asset import source
    tools: tools.yaml
    groups: groups.yaml
---
# maya-asset-source (Pipeline stage)

Asset discovery and resolution for the Maya import pipeline. This skill
produces **`AssetDescriptor`** records that `maya-import-to-scene` consumes
to perform the actual scene import.

## Workflow

```
search_assets(query)  →  [ AssetDescriptor, … ]
resolve_asset(path)   →  AssetDescriptor
         ↓
maya-import-to-scene: import_to_scene(descriptor)
```

## AssetDescriptor schema

Every tool in this skill that returns assets uses the following structure:

```json
{
  "id":        "<uuid or stable path key>",
  "name":      "<display name>",
  "path":      "<absolute file path>",
  "format":    "fbx | obj | usd | ma | mb",
  "size_bytes": 12345,
  "metadata":  {}
}
```

## Scripts

- `search_assets` — Search a directory tree for asset files matching a query
- `resolve_asset` — Resolve a single path or asset ID to an `AssetDescriptor`
