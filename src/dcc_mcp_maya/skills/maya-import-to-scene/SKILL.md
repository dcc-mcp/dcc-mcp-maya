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
up-axis metadata, so an undeclared import is read by Maya as bare numbers in
its internal unit — always **centimetres**, whatever `currentUnit` says. A
2 × 4 × 6 **metre** box therefore lands as 2 × 4 × 6 **centimetres**, and a
Z-up file lies down in a Y-up scene. Geometry is fully intact, so nothing
looks broken.

Because the values arrive as centimetres, a declared `source_unit` is a
straight *source unit → centimetres* conversion. **The target scene unit is
not part of the calculation** — `currentUnit` only changes how those
centimetres are displayed, not how they were read. Measured on Maya 2026: one
hand-written OBJ imported into cm / mm / m / km / in scenes measures `[1, 2, 3]`
centimetres in every one of them.

Declare the source instead and let the tool convert:

| Parameter | Effect |
|-----------|--------|
| `source_unit` | `mm` / `cm` / `m` / `km` / `in` / `ft` / `yd` / `mi`. Scaled so the values become centimetres — Maya's internal unit (see below). |
| `source_up_axis` | `y` or `z`. Rotated to match the target scene up axis (`upAxis -q -axis`). |
| `require_semantics` | `true` fails the import instead of warning when either is undeclared. |

Example — a metres-authored, Z-up OBJ into a centimetre, Y-up scene:

```python
import_to_scene(asset, source_unit="m", source_up_axis="z")
# -> unit_conversion_factor 100.0, axis_conversion "z_to_y"
```

When the source is **not** declared:

- The import still runs, with the values read as centimetres.
- The result carries a `warnings` entry naming the assumption that was
  applied (that the bare numbers are centimetres), and the same text is
  mirrored to Maya's Script Editor via `cmds.warning`.
- `require_semantics=True` turns that warning into a hard error.

### Formats that carry their own semantics

`source_unit` / `source_up_axis` describe the **file**. That only needs saying
for formats which cannot say it themselves — currently **OBJ**. FBX, USD and
the Maya formats (MA / MB) embed their own units and up axis, and Maya's
importer applies that on import.

Measured on Maya 2026 with `FBXResetImport` defaults:

| File | Target scene | Measured |
|------|--------------|----------|
| 1 m cube, FBX (`UnitScaleFactor` 100) | cm | lands at **100 cm** — already converted |
| Y-up FBX, height on Y | Z-up | height lands on **Z** — already aligned |
| hand-written OBJ, bare numbers | cm / mm / m / km / in | lands at **`[1, 2, 3]` cm in all five** — *not* converted, and independent of scene unit |

So for those formats the declaration is **ignored, not applied**: scaling or
rotating again would double-apply and reintroduce the exact silent 100x error
this feature exists to prevent. Passing `source_unit` to an FBX import is
reported as an advisory `warnings` entry; use `unit_scale` /
`axis_conversion` if you genuinely want a manual override.

An ignored-declaration note is advisory only — it does **not** trip
`require_semantics`, which refuses imports made under an *unauthorised*
assumption (an undeclared OBJ), not self-describing ones.

## Known limitation — OBJ `o` groups

Maya's OBJ importer merges every `o` group in a file into a single
transform, and exposes no option to split them (verified on Maya 2026:
`options="mo=1"`, `mo=0`, `groups=1` and `g=1` all yield one transform).
Object separation is therefore **not** handled here; it needs either
pre-splitting the file per group or post-splitting the merged mesh by face
range. Tracked separately.

## Scripts

- `import_to_scene` — Import an AssetDescriptor into the current Maya scene
