---
name: maya-geometry
description: |-
  Interchange stage — FBX / OBJ geometry interchange. Round-trip geometry
  through FBX or OBJ; scene save is owned by maya-scene. The FBX export
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
    - export
    - import
    search-hint: |-
      export FBX, import FBX, export OBJ, file_exists, geometry round trip,
      scene interchange, FBXExport options, bake animation FBX. Use
      maya-scene save_scene for .ma/.mb scene saves.
    depends: []
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
