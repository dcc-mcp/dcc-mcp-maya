---
name: maya-geometry
description: |-
  Interchange stage — scene I/O and FBX / OBJ interchange. Save Maya
  scenes (.ma / .mb) and round-trip geometry through FBX or OBJ. The FBX
  export tool drives every FBXExport* option through the FBX plugin's MEL
  globals, bakes animation by default, and verifies the output file. Use
  for cross-DCC handoff. Not for primitive creation (maya-primitives) or
  shot packaging (maya-shot-export).
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
    - save
    - export
    - import
    search-hint: |-
      save Maya scene, save .ma .mb, export FBX, import FBX, export OBJ,
      file_exists, geometry round trip, scene interchange, FBXExport options,
      bake animation FBX
    aliases:
    - maya-interchange
    - maya-io
    - maya-fbx
    side-effects:
    - reads-scene
    - reads-disk
    - writes-disk
    - calls-fbx-plugin
    depends: []
    tools: tools.yaml
    groups: groups.yaml
---
# maya-geometry (Interchange stage)

Scene I/O and geometry interchange. Despite the legacy name `maya-geometry`,
the responsibility is **interchange**, not modelling — see the alias list
in the frontmatter (`maya-interchange`, `maya-io`, `maya-fbx`).

## Why this stage exists

Once an Authoring-stage skill has produced geometry / animation, you
need a reliable way to (a) save the Maya scene file and (b) hand the
geometry off to other DCCs or downstream pipelines. That is what the
Interchange stage handles. Every export tool here:

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

## Groups

- **core** (`default_active: true`) — `file_exists`. Pure filesystem,
  no Maya state.
- **geometry** (`default_active: true`) — main-thread Maya scene save +
  FBX/OBJ import / export.

## Scripts

- `save_scene` — Save the current scene as Maya ASCII or Maya Binary
- `file_exists` — Check whether a file exists on disk (no Maya state)
- `export_fbx` — Export the scene or current selection to FBX with full FBXExport* control
- `import_fbx` — Import an FBX into the current scene; returns new node names
- `export_obj` — Export the scene to OBJ
