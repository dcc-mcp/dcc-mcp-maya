---
name: maya-geometry
description: |-
  Interchange stage — FBX / OBJ / Alembic / USD geometry interchange. Import
  native USD nodes with Maya USD; scene save is owned by maya-scene. The FBX export
  tool drives every FBXExport* option through the FBX plugin's MEL globals,
  bakes animation by default, and verifies the output file. Use for cross-DCC
  handoff. Not for primitive creation (maya-primitives) or shot packaging
  (maya-shot-export).
license: MIT
allowed-tools: Bash Read
metadata:
  dcc-mcp:
    dcc: maya
    layer: domain
    stage: interchange
    version: 2.0.0
    tags:
    - maya
    - geometry
    - interchange
    - fbx
    - obj
    - usd
    - alembic
    - export
    - import
    search-hint: |-
      export FBX, import FBX OBJ Alembic USD, SpeedTree geometry, file_exists, geometry round trip,
      scene interchange, FBXExport options, bake animation FBX. Use
      maya-scene save_scene for .ma/.mb scene saves.
    tools: tools.yaml
    groups: groups.yaml
    recipes: references/IO_CHECKLIST.md
---
# maya-geometry (Interchange stage)

Geometry interchange. Despite the legacy name `maya-geometry`, the
responsibility is **interchange**, not modelling or native scene-file
persistence. Search hints include `maya-interchange`, `maya-io`, and
`maya-fbx` for legacy discovery paths.

## Why this stage exists

Once an Authoring-stage skill has produced geometry / animation, you
need a reliable way to hand geometry off to other DCCs or downstream
pipelines. That is what the Interchange stage handles. Native `.ma` / `.mb`
scene saves are intentionally routed through `maya_scene__save_scene`.
Every export tool here:

- pushes its full option surface through the official MEL globals (no
  silent reliance on plugin defaults);
- bakes animation by default for FBX so downstream apps see the same
  motion the artist sees;
- verifies the destination file (existence + non-zero bytes) and
  surfaces the size in the result envelope.

## Cross-Maya FBX contract (P0)

When handing FBX to **another Maya year** or a different DCC, treat these fields as mandatory knobs—not plugin defaults:

| Parameter | Guidance |
|-----------|------------|
| `fbx_version` | Pin a concrete enum value (e.g. `FBX202000`) so source and target agree on file format. |
| `bake_animation` | Keep `true` whenever motion comes from IK, constraints, expressions, or simulation; otherwise downstream may see static meshes. |
| `start_frame` / `end_frame` | Set explicitly to the bake window you need for production; do not rely on UI playback range alone. |
| `up_axis` | Set `y` or `z` explicitly when your pipeline requires a fixed world orientation. |

The `export_fbx` script resets the FBX plugin option store (`FBXResetExport`) before export and returns `applied_options` plus `size_bytes` in the success envelope for audit and regression triage.

## Import acceptance

`import_file` loads the required translator plugin for FBX (`fbxmaya`), OBJ
(`objExport`), Alembic (`AbcImport`), and USD/USDA/USDC (`mayaUsdPlugin`).
Missing plugins return an error before import. USD creates native Maya nodes;
use `maya-asset-sync` when a USD proxy stage is required.

Import jobs are asynchronous. Use CLI `call --wait`, or query the returned
core job id with `jobs_get_status` until terminal, then inspect the inner
result's `success` and `context.imported_nodes`. A queued job or completed
transport is insufficient. These native translators are monolithic:
cancellation does not pre-empt a running native import. After a timeout,
query the existing job before retrying to avoid duplicate imports.

Read back imported geometry using `list_objects`, `get_bounding_box`,
`get_poly_count`, `get_uv_info`, and `get_shader_assignment`. Compare with
the source asset manifest. Node creation alone does not verify material
textures, source units/axis, LOD switching, or wind animation. See
[`docs/guide/capability-audit.md`](../../../../docs/guide/capability-audit.md)
for the remaining acceptance gaps.

## Bulk and multi-file export (agents)

For **N separate FBX paths** (e.g. one file per root transform), prefer **one** `execute_python` payload that loops in Maya, applies the **Cross-Maya FBX contract** fields each iteration, and returns e.g. `context.written_files`. Invoking the `export_fbx` tool **N times** over MCP is possible when each call must be individually validated, but it costs **N round-trips** — collapse to a single script when the user only needs throughput and deterministic naming.

## Groups

- **core** (`default_active: true`) — `file_exists`. Pure filesystem,
  no Maya state.
- **geometry** (`default_active: true`) — main-thread FBX/OBJ import / export.

## Scripts

- `file_exists` — Check whether a file exists on disk (no Maya state)
- `export_fbx` — Export the scene or current selection to FBX with full FBXExport* control
- `import_file` — Import generic Maya-recognised scene / geometry files
- `import_fbx` — Import an FBX into the current scene; returns new node names
- `export_obj` — Export the scene to OBJ
