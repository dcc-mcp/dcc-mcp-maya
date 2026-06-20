---
name: maya-import-to-scene
description: |-
  Interchange stage — import assets into the Maya scene using typed
  AssetDescriptor contracts. Consumes FBX / OBJ / USD / GLTF / GLB / ABC
  formats exported from any DCC, places them with configurable namespace
  and transform hints, and returns the imported node list. Supports
  material modes (as_authored / default_gray / skip) and skip-existing
  dedup by asset_id. Does NOT handle scene saving or pipeline publishing
  — use maya-pipeline for that.
license: MIT
allowed-tools: Bash Read
metadata:
  dcc-mcp:
    dcc: maya
    layer: domain
    stage: interchange
    version: 1.0.0
    tags:
    - maya
    - import
    - interchange
    - fbx
    - obj
    - usd
    - asset
    - material
    search-hint: |-
      import asset, import to scene, import FBX, import OBJ, import USD,
      import GLTF, import GLB, import Alembic, asset descriptor, AssetDescriptor,
      skip existing, material mode, placement, as_authored, default_gray.
    tools: tools.yaml
    groups: groups.yaml
    depends:
    - maya-geometry
---
# maya-import-to-scene (Interchange stage)

Import assets into Maya using typed `AssetDescriptor` contracts from
`dcc-mcp-core`. This is the **typed counterpart** to the raw `import_file`
/ `import_fbx` tools in `maya-geometry` — it accepts structured descriptors
and applies material, placement, and dedup semantics in a single call.

## Why this skill exists

`maya-geometry` provides low‑level FBX / OBJ import tools with raw
path + namespace arguments. `maya-import-to-scene` wraps those with the
`dcc_mcp_core.asset_import` contract layer:

| Aspect | `maya-geometry` | `maya-import-to-scene` |
|--------|-----------------|------------------------|
| Input shape | `file_path`, `namespace`, … | `AssetDescriptor` + `ImportToSceneRequest` |
| Material handling | none (plugin defaults) | `as_authored`, `default_gray`, `skip` |
| Skip-existing | none | dedup by `asset_id` |
| Placement | `group_name` only | `PlacementHint` (translate / rotate / scale / parent) |
| Error envelope | `maya_success` / `maya_error` | `ImportToSceneResult` (warnings included) |

## Material modes

- **as_authored** — Keep the file's embedded materials (FBX, GLTF
  shaders, etc.). Connects to Maya's standard surface / lookdev nodes
  when possible.
- **default_gray** — Replace all materials with a neutral gray
  `lambert1`.  Useful for look-dev handoff or lighting tests.
- **skip** — Discard material data; only import geometry transforms.

## Skip-existing dedup

When `ImportToSceneRequest.skip_existing = True`, the script checks
whether a node tagged with the same `asset_id` already exists in the
scene (via Maya's attribute `dcc_mcp_asset_id`).  If found, the import
is skipped and a warning is returned.

## Format support

Dispatches based on `AssetFileVariant.format`:

| Format | Maya import path |
|--------|-----------------|
| `FBX`  | `import_fbx` via FBX plugin |
| `OBJ`  | `import_file` via OBJ plugin |
| `USD` / `USDZ` | `mayaUsdPlugin` / `cmds.file` (USD import) |
| `GLTF` / `GLB` | `gltfPlugin` / raw file import |
| `ABC`  | `AbcImport` / Alembic plugin |
| `BLEND` | **unsupported** — returns an error |
| `UNKNOWN` | Falls back to `import_file` |

## Groups

- **import** (`default_active: true`) — Main-thread asset import.

## Scripts

- `import_to_scene` — Main entry point: accepts `ImportToSceneRequest`,
  imports the best variant, applies material mode and placement, and
  returns `ImportToSceneResult`.
