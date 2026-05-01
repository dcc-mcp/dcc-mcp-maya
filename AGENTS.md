# AGENTS.md — dcc-mcp-maya Agent Navigation Map

> Progressive disclosure: this file is a **map**, not an encyclopedia.
> Follow the links for depth. Stay here for breadth.

---

## 30-Second Summary

`dcc-mcp-maya` embeds a standards-compliant MCP Streamable HTTP server directly inside Autodesk Maya. It exposes 73+ Maya operations as MCP tools that any AI agent (Claude, Cursor, Gemini, etc.) can call over HTTP — no external gateway, no subprocess bridge.

**Current version:** 0.2.24 <!-- x-release-please-version -->
**Core dependency:** `dcc-mcp-core>=0.14.21,<1.0.0`
**Python:** 3.7+
**Maya:** 2020+

---

## Quick Start (3 Lines)

```python
import dcc_mcp_maya
handle = dcc_mcp_maya.start_server(port=8765)
# MCP client connects to http://127.0.0.1:8765/mcp
```

Or load the Maya plugin (`dcc_mcp_maya_plugin.py`) and the server starts automatically.

---

## Information Layers — Pick Your Depth

### Layer 1 — You Are a User / Operator
*Goal: Install, configure, and connect an MCP host.*

- **README.md** — Installation, quick start, environment variables, bundled skills list.
- **docs/guide/getting-started.md** — Step-by-step for first-time users.
- **docs/guide/installation.md** — Plugin mode, `userSetup.py`, multi-Maya setup.
- **docs/guide/multi-instance.md** — Run multiple Maya sessions behind one gateway.
- **docs/guide/mcp-tools.md** — Representative tool inventory (scene, geometry, material, animation, render).

### Layer 2 — You Are a Skill Author
*Goal: Write new Maya automation skills and register them as MCP tools.*

- **docs/guide/contributing.md** — Skill package layout, `SKILL.md` format, action script rules.
- **docs/guide/advanced.md** — Custom skills, main-thread scheduling, hot-reload.
- **src/dcc_mcp_maya/api.py** — 18 high-level helpers (`maya_success`, `with_maya`, `validate_node_exists`, `require_param`, …).
- **Key pattern:** Lazy-import `maya.cmds` inside the function so skills can be discovered without a running Maya.

Minimal skill template:
```python
from dcc_mcp_maya.api import maya_success, maya_error, with_maya

@with_maya
def create_sphere(radius: float = 1.0) -> dict:
    import maya.cmds as cmds
    result = cmds.polySphere(radius=radius)
    return maya_success("Created sphere", object_name=result[0])
```

### Layer 3 — You Are a Core Developer
*Goal: Modify the server, dispatcher, or plugin behavior.*

- **src/dcc_mcp_maya/server.py** — `MayaMcpServer` composition root (constructor, `register_builtin_actions`, `start`, `stop`, metrics, job persistence). Heavy lifting lives in private siblings: `_env`, `_executor`, `_skill_loader`, `_version_probe`, `_transport`, `_pyexec`, `_stale_cleanup`.
- **src/dcc_mcp_maya/dispatcher/** — `MayaUiDispatcher`, `MayaStandaloneDispatcher`, `MayaUiPump`, `check_maya_cancelled` (split into `job` / `cancel` / `ui` / `standalone` / `pump` submodules — public symbols re-exported from the package).
- **maya/plugin/dcc_mcp_maya_plugin.py** — Maya plugin entry point (`initializePlugin`, `uninitializePlugin`, menu, gateway auto-config).
- **tests/** — 50+ unit tests, E2E tests (tahv/mayapy 2022–2025), multi-instance gateway tests.
- **Upstream `dcc-mcp-core` API reference** — https://github.com/loonghao/dcc-mcp-core/blob/main/llms.txt — authoritative one-page index of every public symbol re-used by this repo (`DccServerBase`, `MinimalModeConfig`, `BaseDccCallableDispatcher`, `register_inprocess_executor`, `is_gui_executable` / `correct_python_executable`, `FileRegistry`, `check_dcc_cancelled`, `JobHandle`, result-envelope factories, etc.). Always consult this first before adding a new helper locally — most "missing" utilities already exist upstream and are simply waiting to be wired in.

### Layer 4 — You Are an AI Agent Reading This
*Goal: Discover and use tools effectively inside a live Maya session.*

- **llms.txt** — Core API surface, environment variables, key files (fits in a small context window).
- **llms-full.txt** — Complete public API signatures, all environment variables, 12 built-in skill categories.
- **Upstream core reference** — https://github.com/loonghao/dcc-mcp-core/blob/main/llms.txt (and the deeper [`llms-full.txt`](https://github.com/loonghao/dcc-mcp-core/blob/main/llms-full.txt)) — exhaustive `dcc_mcp_core` API surface; use it whenever a tool/skill needs to leverage core primitives that are not surfaced in this repo's own `llms.txt`.
- **Skill discovery workflow:**
  1. Call `search_tools(query="bevel")` or `find_skills("bevel")` to locate relevant skills.
  2. Call `load_skill("maya-mesh-ops")` to materialize the skill's tools.
  3. Call `activate_group("extended")` if additional tool groups are available.
  4. Execute the specific tool (e.g., `maya_mesh_ops__bevel_edge`).
- **Always check cancellation in long-running loops:**
  ```python
  from dcc_mcp_maya import check_maya_cancelled
  for frame in frames:
      check_maya_cancelled()   # raises CancelledError when cancelled
      cmds.currentTime(frame)
      cmds.render()
  ```

---

## Project-State Persistence (issue #576 / core 0.14.21)

The Maya adapter wires `dcc_mcp_core.register_project_tools` into `MayaMcpServer.register_builtin_actions()`, exposing four MCP tools that persist a Maya scene's working set under `<scene_dir>/.dcc-mcp/project.json`:

| Tool             | Purpose                                                                 |
|------------------|-------------------------------------------------------------------------|
| `project.save`   | Persist current state (loaded assets, active skills/tool-groups, checkpoint IDs, free-form metadata) for a given `scene_path`. |
| `project.load`   | Read an existing `project.json` (returns failure when absent — never auto-creates). |
| `project.resume` | Return the rehydration payload (scene path, assets, skills, tool groups, checkpoints, session id, timestamps, project dir) an agent needs to restore a session across Maya restarts. |
| `project.status` | Pure read: current state + project_dir + state_path. |

Key Python symbols:

```python
from dcc_mcp_maya import (
    ENV_PROJECT_TOOLS,        # "DCC_MCP_MAYA_PROJECT_TOOLS" — set "0" to disable
    MayaSceneResolver,        # strategy: returns current scene path or None
    ProjectToolsIntegration,  # SOLID binder used by the server
    attach_project_tools,     # one-shot helper invoked from register_builtin_actions
)
```

Operator opt-out: `DCC_MCP_MAYA_PROJECT_TOOLS=0`.  Each `project.*` entry adds <800 B to `tools/list` and is guaranteed safe to register before any dispatcher is attached (pure filesystem operations, never touches `maya.cmds`).

---

## Gateway Capability Surface (issues #163 / #164 / #165)

The Maya adapter publishes a **compact capability manifest** so the gateway — and agents that query Maya directly — can enumerate every action (loaded *and* unloaded) without paying the cost of full per-tool JSON Schemas.

Entry points:

| Surface                             | Where                                                                                                                          |
|-------------------------------------|--------------------------------------------------------------------------------------------------------------------------------|
| Programmatic                        | `MayaMcpServer.build_capability_manifest(loaded_only=False)`                                                                   |
| MCP tool (agents)                   | `dcc_capability_manifest({"loaded_only": bool})` — registered before `start()`                                                 |
| Record shape                        | `{tool_slug, backend_tool, skill_name, summary (<=200 ch), tags, execution, affinity, timeout_hint_secs, has_schema, group}`   |
| Live sync                           | `publish_capability_snapshot(reason=...)` invoked automatically on `start()` / `load_skill` / `unload_skill`                   |
| Scene context (→ REST `/v1/context`)| `MayaContextSnapshotProvider` wired via `set_context_snapshot_provider` in `__init__`                                          |

Each record is **<= 640 B** serialised JSON and omits `inputSchema` — roughly 4× cheaper than a full `tools/list` entry.  The manifest deliberately exposes skill actions that MCP `tools/list` intentionally skips (core only emits `__skill__*` stubs there), so an agent can decide which skill to load without polling.

Key Python symbols exported from the top-level package:

```python
from dcc_mcp_maya import (
    MayaCapabilityManifestBuilder,   # catalog → list[CapabilityRecord]
    CapabilityRecord,
    build_manifest_payload,
    register_capability_mcp_tool,
    MayaContextSnapshotProvider,
    collect_gateway_metadata,
    make_snapshot_provider,
)
```

---

## Key Conventions

### Tool Naming
- Action name = `{skill_name.replace("-","_")}__{script_stem}`
- Example: skill `maya-scene` + script `new_scene.py` → tool `maya_scene__new_scene`

### Result Format (Return from Skill Scripts)
Use helpers from `dcc_mcp_maya.api`:
- `maya_success(message, **context)` → `{"success": True, "message": ..., "context": {...}}`
- `maya_error(message, error, possible_solutions=[...], **context)` → `{"success": False, ...}`
- `maya_from_exception(exc, message, **context)` → includes full traceback (preferred over `str(exc)`)

### Execution & Affinity (tools.yaml)
Every tool declaration **must** include:
```yaml
tools:
  - name: render_frames
    execution: async          # sync | async
    affinity: main            # main | any
    timeout_hint_secs: 600    # required when execution: async
```
| Value | When to Use |
|-------|-------------|
| `execution: async` | Typical wall-clock > 2s (render, bake, cache, simulation). Must set `timeout_hint_secs`. |
| `execution: sync` | Fast queries, attribute setters, small creations. |
| `affinity: main` | Anything importing `maya.*` or touching scene state. Safe default. |
| `affinity: any` | Pure filesystem / pure Python that never touches Maya. |

The adapter now **honors `affinity: any` at runtime**: such actions execute
inline on the HTTP worker thread instead of being queued behind the Maya
UI dispatcher, freeing the main thread for viewport work.  Resolution is
done once per script by `dcc_mcp_maya._affinity.resolve_affinity`
(reads the co-located `tools.yaml` — safe-defaults to `main` on any
lookup failure).

### Minimal Mode (Default)
At startup only 2 skills are fully loaded: `maya-scripting` and `maya-scene` (core groups only).
All other skills appear as `__skill__<name>` stubs. Call `load_skill(name)` to activate on demand.

### Environment Variables (Maya-Specific)
| Variable | Default | Purpose |
|----------|---------|---------|
| `DCC_MCP_MAYA_PORT` | `8765` | TCP port for MCP HTTP server. |
| `DCC_MCP_MAYA_SERVER_NAME` | `maya-mcp` | Name in MCP `initialize` response. |
| `DCC_MCP_MAYA_SKILL_PATHS` | — | Extra skill directories (`;` on Windows, `:` on Unix). |
| `DCC_MCP_MAYA_MINIMAL` | `1` | `0` = preload all skills; `1` = minimal startup. |
| `DCC_MCP_MAYA_DEFAULT_TOOLS` | — | Comma-separated skill names to preload (overrides minimal). |
| `DCC_MCP_MAYA_METRICS` | `0` | `1` = enable Prometheus `/metrics` endpoint. |
| `DCC_MCP_MAYA_JOB_STORAGE` | `<data_dir>/jobs.db` | SQLite job persistence path. |
| `DCC_MCP_MAYA_JOB_RECOVERY` | `drop` | `requeue` = resume idempotent jobs on startup. |
| `DCC_MCP_GATEWAY_PORT` | `9765` | Multi-instance gateway election port. `0` = disable. |
| `DCC_MCP_REGISTRY_DIR` | OS temp dir | Shared service-discovery registry directory. |

---

## FAQ / Common Pitfalls

**Q: The MCP host says "tool not found" even though the skill exists.**  
A: In minimal mode, skills are stubs until `load_skill("maya-primitives")` is called. Load the skill first.

**Q: A tool that uses `maya.cmds` crashes when run from a worker thread.**  
A: The tool's `tools.yaml` must declare `affinity: main`. Anything touching Maya state must run on the UI thread.

**Q: How do I make a long-running render cancellable?**  
A: Poll `check_maya_cancelled()` inside the loop. It raises `CancelledError` when the client or dispatcher signals cancellation.

**Q: How do I start the server in a Maya batch / `mayapy` script?**  
A: Same API — `dcc_mcp_maya.start_server(port=0)`. In batch mode the `MayaStandaloneDispatcher` runs jobs on the calling thread directly.

**Q: Where are the built-in skills?**  
A: `src/dcc_mcp_maya/skills/` (12 packages, 73 scripts). Each package contains `SKILL.md`, `tools.yaml`, `groups.yaml`, and `scripts/*.py`.

---

## File Index (Agent Quick-Look)

| File | Role |
|------|------|
| `README.md` | Human-facing overview, installation, config tables |
| `llms.txt` | Condensed AI reference (this project's "man page") |
| `llms-full.txt` | Exhaustive API reference |
| `src/dcc_mcp_maya/__init__.py` | Public API exports |
| `src/dcc_mcp_maya/server.py` | `MayaMcpServer` composition root — lifecycle, discovery, metrics, jobs |
| `src/dcc_mcp_maya/_env.py` | `DCC_MCP_MAYA_*` env-var resolution helpers |
| `src/dcc_mcp_maya/_executor.py` | In-process skill execution + handler registration (respects `_affinity`) |
| `src/dcc_mcp_maya/_affinity.py` | Per-action thread-affinity lookup from sibling `tools.yaml` |
| `src/dcc_mcp_maya/_skill_loader.py` | Minimal-mode skill loading (constants + loaders) |
| `src/dcc_mcp_maya/_version_probe.py` | Maya availability + version string detection |
| `src/dcc_mcp_maya/_transport.py` | `TransportManager` wrappers (bind / find / rank) |
| `src/dcc_mcp_maya/_pyexec.py` | Auto-correct `DCC_MCP_PYTHON_EXECUTABLE` (issue #125) |
| `src/dcc_mcp_maya/_stale_cleanup.py` | Stale FileRegistry detection + warning (issue #126) |
| `src/dcc_mcp_maya/_project_tools.py` | `register_project_tools` integration — `project.save/load/resume/status` MCP tools (issue #576 / core 0.14.21) |
| `src/dcc_mcp_maya/dispatcher/` | Thread-affinity dispatchers + cancellation (directory module) |
| `src/dcc_mcp_maya/api.py` | Skill authoring helpers |
| `src/dcc_mcp_maya/plugin.py` | Maya plugin (`initializePlugin` / menu) |
| `src/dcc_mcp_maya/skills/` | 12 built-in skill packages, 73 scripts |
| `docs/` | VitePress documentation site (EN + ZH) |
| `tests/` | pytest suite (unit + E2E + integration) |

**New in 0.2.20:** Rust-backed dispatchers (`PyPumpedDispatcher`, `PyStandaloneDispatcher`, `_CorePump`, `create_pumped_dispatcher`) provide higher performance via Rust core (requires `dcc-mcp-core>=0.14.17`). See `llms-full.txt` for details. |
