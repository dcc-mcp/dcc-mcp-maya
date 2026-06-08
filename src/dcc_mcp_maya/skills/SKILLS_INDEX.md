# Maya Skills Index

> Cross-skill navigation map. Read this before deciding which skill to load.

The 25 bundled skills are organised into **five stages** that match the
mental model of a Maya pipeline. Each skill carries the stage in its
SKILL.md frontmatter under `metadata.dcc-mcp.stage`.

## The five stages

| Stage | Purpose | Default loaded? | Skills |
|-------|---------|-----------------|--------|
| `bootstrap` | Escape hatch; arbitrary code only when no typed skill fits. | yes | `maya-scripting` |
| `scene` | Scene file lifecycle, DAG navigation, attributes, node graph, viewport visibility. | partial (`maya-scene` only) | `maya-scene`, `maya-scene-assembly`, `maya-display`, `maya-attributes`, `maya-node-graph` |
| `authoring` | Create / edit content: meshes, UVs, materials, rigs, animation, dynamics, light rigs. | no | `maya-primitives`, `maya-mesh-ops`, `maya-uv-ops`, `maya-materials`, `maya-material-library`, `maya-texture-bake`, `maya-rigging`, `maya-animation`, `maya-dynamics`, `maya-pose-library`, `maya-expressions`, `maya-light-rig` |
| `interchange` | Move geometry / scenes across DCCs (FBX, OBJ, presets, save). | no | `maya-geometry`, `maya-export-preset` |
| `pipeline` | Production pipeline: project, publish, shot export, render, render farm, development diagnostics. | no | `maya-dev`, `maya-pipeline`, `maya-shot-export`, `maya-render`, `maya-render-farm` |

## Deciding which skill to load

Ask yourself, in order:

1. **What does the user want to *produce*?**
   - A file on disk? → start with the **interchange** or **pipeline** skill that owns that file.
   - A change inside the current scene? → start with the **authoring** skill that owns that change.
   - A query / inspection? → start with the **scene** skill (`maya-scene`, `maya-attributes`, `maya-node-graph`).
2. **Match a domain skill first:** `search_skills(query=...)` (or `dcc_capability_manifest` / `search_tools` on the gateway) → `load_skill(...)` → call the **typed** tool (`inputSchema` + annotations). This is the default path for stability and crash avoidance.
3. **Runtime plug-in lifecycle:** use `maya-scripting` typed tools `list_plugins`, `load_plugin`, and `unload_plugin` before falling back to arbitrary script snippets.
4. **Only when no skill fits** (bulk homogeneous loop, OpenMaya-only gap, quick one-off): load `maya-scripting` and use `execute_python` / `execute_mel`, optionally guided by `maya-scripting/references/RECIPES.md`.

## Bulk import, export, and naming

For **N similar operations** (many FBX/OBJ writes, batch rename, procedural primitives):

1. Prefer **`load_skill`** once, then either **typed export / modelling tools** (schema-validated) **or** a **single** `execute_python` loop when MCP round-trips would dominate and you accept weaker validation — return `written_files` / errors in `context`.
2. **Gateway** users: use `call_tools` / `/v1/call_batch` for a **short** chain of different tools (≤25), not as a substitute for a local loop over identical exports.
3. When mixing approaches, load domain skills **once** (`load_skill("maya-geometry")`) then either call typed export tools **or** mirror the same FBX flags inside your script (see `maya-geometry/SKILL.md` contract).
4. Pass **absolute paths** and a **naming rule** (prefix, zero-padded index, shot/asset ids) as structured arguments.

Full rationale: repo root `AGENTS.md` § *Bulk import, export, and naming*; example: `examples/workflows/maya_bulk_rbd_fbx.md`.

## Common task → skill chains

| Task | Skill chain |
|------|-------------|
| Create N spheres with random transforms, add gravity/rigid bodies, bake bounce animation, export FBX, import in another Maya | Prefer **`load_skill`** chain: `maya-primitives` → `maya-dynamics` → `maya-animation` → `maya-geometry` (`export_fbx` / `import_fbx`). Use **one** `execute_python` only when round-trip count would dominate latency and you accept weaker validation |
| Build a rig, detect optional rig frameworks, copy skin weights, animate, and send to render farm | `maya-rigging` (`detect_rig_frameworks`, `create_rig_control`, `create_constraint`, `copy_skin_weights`) → `maya-animation` → `maya-render-farm` |
| Look-dev a hero asset, save material preset | `maya-materials` → `maya-material-library` |
| Publish an asset version | `maya-pipeline` (uses `maya-geometry` under the hood; declared in `depends`) |
| Bake AO maps from high-res to low-res | `maya-uv-ops` → `maya-texture-bake` |
| Create a single light or three-point rig and tweak intensity | `maya-light-rig` (`create_light`, `create_three_point_rig`, `set_light_rig_intensity`) |
| Render an image, snapshot the viewport, write an MP4 preview, or collect debug evidence | **Intent-driven:** `maya-render` (`render_frame` for final-frame output, `debug_scene_snapshot` for diagnostics, `playblast_to_mp4` for animation preview). See `maya-render/SKILL.md` § *Render intents → tool routing* and § *VP2 fallback flow* for error recovery when viewport is unavailable. |
| Develop and debug a Maya Python tool inside the live session | `maya-dev` (`attach_project` → `run_check`; optional `start_debugpy`) |

## Side-Effect Taxonomy

Tool-level `tools.yaml` entries declare execution and thread affinity. Treat
the operation descriptions and tags as the source of truth for side effects:

- `reads-scene` — calls `maya.cmds` queries; safe.
- `writes-scene` — mutates DAG / DG state; should run on the main thread.
- `reads-disk` / `writes-disk` — touches the filesystem.
- `calls-fbx-plugin` — depends on the bundled FBX plugin being available.
- `calls-external-service` — talks to a non-Maya service (e.g. Deadline).
- `executes-arbitrary-code` — `maya-scripting` only.
- `heavy-cpu` — long-running; set realistic `timeout_hint_secs`.

An agent can use these signals to:

* warn the user before destructive operations,
* batch read-only queries,
* avoid blasting `executes-arbitrary-code` skills when a typed alternative exists.

## Cross-cutting safety nets

Maya AutoSave is **persistently disabled** at plug-in load time, then
restored on unload — see
[`_disable_autosave_for_session`](../../../maya/plugin/dcc_mcp_maya_plugin.py).
This neutralises the one dialog Maya pops *unprompted* during a long-
running session (the unsaved-scene AutoSave save-prompt) and removes the
between-jobs race window the older per-job AutoSave snooze suffered from.
Opt out via `DCC_MCP_MAYA_DISABLE_AUTOSAVE=0`.

The previous `dcc_mcp_maya._safe_session.mcp_safe_session` context
manager has been **removed** (2026-05-16):

* The `cmds.confirmDialog` / `promptDialog` / `fileDialog` /
  `fileDialog2` / `layoutDialog` monkey-patch was crashing Maya
  whenever its C++ engine consumed those same entries internally
  (`cmds.file(new=True)`, Arnold renderer switch, reference machinery).
* The per-job AutoSave snooze migrated to the persistent session-wide
  disable above.
* With both responsibilities gone, the wrapper was a no-op. Removing
  it brings the dispatch path in line with PatrickPalmer/maya-mcp-server,
  which never wrapped `cmds.*` calls and has been the stability
  benchmark for this fix series.

The mitigation for an MCP-dispatched job that genuinely opens a modal
dialog is now a **server-side request timeout**: the gateway cancels
the call after N seconds and surfaces `cancelled` to the agent, while
the user dismisses the dialog inside Maya. Set
`DCC_MCP_MAYA_SAFE_SESSION=0` to disable this for an interactive
authoring session.

## Discovery Terms

Skill discovery terms live in `metadata.dcc-mcp.search-hint` and `tags`, using
only metadata keys accepted by the current gateway/core parser. For example,
`maya-geometry` includes `maya-interchange`, `maya-io`, and `maya-fbx` in its
search hint so legacy names still match without emitting unknown-key warnings.
