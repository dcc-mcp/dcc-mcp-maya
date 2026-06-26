---
name: maya-import-to-scene
description: |-
  Pipeline stage — structured asset import. Consume an AssetDescriptor
  produced by maya-asset-source and import the asset (FBX, OBJ, USD)
  into the current Maya scene via cmds.file(). Handles axis/unit
  conversion, MaterialMode, PlacementHint, and optional target collection
  grouping. Returns an ImportToSceneResult with the new node list.
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
    - import
    - asset
    - pipeline
    - fbx
    - obj
    - usd
    search-hint: |-
      import asset to scene, import FBX pipeline, import OBJ pipeline,
      import USD Maya, AssetDescriptor import, ImportToSceneResult,
      axis conversion import, unit conversion import, material mode,
      placement hint, target collection, asset import pipeline
    tools: tools.yaml
    groups: groups.yaml
    depends:
    - maya-asset-source
---
# maya-import-to-scene (Pipeline stage)

Structured asset import for the Maya import pipeline. This skill
consumes **`AssetDescriptor`** records from `maya-asset-source` and
writes geometry into the current scene, returning an
**`ImportToSceneResult`**.

## Typical workflow

```
maya-asset-source: search_assets / resolve_asset
         ↓  AssetDescriptor
import_to_scene(descriptor, axis_conversion=..., material_mode=..., ...)
         ↓  ImportToSceneResult
```

## ImportToSceneResult schema

```json
{
  "asset_id":            "<id from descriptor>",
  "asset_name":          "<name>",
  "path":                "<absolute path>",
  "format":              "fbx | obj | usd | ma | mb",
  "imported_short_names": ["mesh1", "rig1"],
  "imported_long_names":  ["|mesh1", "|rig1"],
  "top_level_groups":    ["|asset_grp"],
  "size_bytes":          12345,
  "axis_conversion":     "none | y_to_z | z_to_y",
  "unit_scale":          1.0,
  "material_mode":       "preserve | assign_lambert | skip",
  "placement_hint":      "origin | selection | custom",
  "target_collection":   null
}
```

## MaterialMode

| Value | Behaviour |
|-------|-----------|
| `preserve` | Keep materials as imported (default). |
| `assign_lambert` | After import, assign a default Lambert shader to all new mesh shapes. |
| `skip` | Strip material assignments after import. |

## PlacementHint

| Value | Behaviour |
|-------|-----------|
| `origin` | Leave imported nodes at the position encoded in the file (default). |
| `selection` | Move the top-level group to the current selection's world-space pivot. |
| `custom` | Translate the top-level group to `custom_position` [x, y, z]. |

## Axis / unit conversion

Maya natively reads the axis and unit stored in FBX. The `axis_conversion`
parameter is a **post-import override** applied via `cmds.xform` on every
top-level transform when you need to correct mismatches:

| Value | Effect |
|-------|--------|
| `none` | No post-import transform (default). |
| `y_to_z` | Rotate top-level transforms 90° around X (convert Y-up → Z-up). |
| `z_to_y` | Rotate top-level transforms −90° around X (convert Z-up → Y-up). |

`unit_scale` applies a uniform scale to every top-level transform (e.g.
`0.01` to convert cm → m).

## Scripts

- `import_to_scene` — Import an AssetDescriptor into the current Maya scene
