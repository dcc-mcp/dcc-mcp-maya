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
  "target_collection":   null,
  "source_unit":         "m",
  "source_up_axis":      "z",
  "target_unit":         "cm",
  "target_up_axis":      "y",
  "unit_conversion_factor": 100.0,
  "warnings":            []
}
```

`source_unit` / `source_up_axis` are whatever the caller declared (or
`null`); `target_unit` / `target_up_axis` are read from the live scene.
`warnings` is non-empty whenever an assumption had to be made.

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

## Declared source semantics (`source_unit` / `source_up_axis`)

`axis_conversion` and `unit_scale` are *manual knobs*: the caller has to
already know what the file is authored in. OBJ carries neither unit nor
up-axis metadata, so an undeclared import is silently read in whatever the
target scene happens to use — a 2 × 4 × 6 **metre** box lands as 2 × 4 × 6
**centimetres** in a centimetre scene, and a Z-up file lies down in a
Y-up scene. Geometry is fully intact, so nothing looks broken.

Declare the source instead and let the tool convert:

| Parameter | Effect |
|-----------|--------|
| `source_unit` | `mm` / `cm` / `m` / `km` / `in` / `ft` / `yd` / `mi`. Scaled into the target scene unit (`currentUnit -q -linear`). |
| `source_up_axis` | `y` or `z`. Rotated to match the target scene up axis (`upAxis -q -axis`). |
| `require_semantics` | `true` fails the import instead of warning when either is undeclared. |

Example — a metres-authored, Z-up OBJ into a centimetre, Y-up scene:

```python
import_to_scene(asset, source_unit="m", source_up_axis="z")
# -> unit_conversion_factor 100.0, axis_conversion "z_to_y"
```

When the source is **not** declared:

- The import still runs, using the target scene's unit and orientation.
- The result carries a `warnings` entry naming the assumption that was
  applied, and the same text is mirrored to Maya's Script Editor via
  `cmds.warning`.
- `require_semantics=True` turns that warning into a hard error.

Warnings are only raised for formats that cannot carry the metadata. FBX,
USD and Maya ASCII/Binary describe their own units and axis, so they stay
quiet unless you explicitly override them.

## Known limitation — OBJ `o` groups

Maya's OBJ importer merges every `o` group in a file into a single
transform, and exposes no option to split them (verified on Maya 2026:
`options="mo=1"`, `mo=0`, `groups=1` and `g=1` all yield one transform).
Object separation is therefore **not** handled here; it needs either
pre-splitting the file per group or post-splitting the merged mesh by face
range. Tracked separately.

## Scripts

- `import_to_scene` — Import an AssetDescriptor into the current Maya scene
