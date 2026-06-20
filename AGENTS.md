# AGENTS.md — dcc-mcp-maya Agent Navigation Map

> Progressive disclosure: this file is a **map**, not an encyclopedia.
> Follow the links for depth. Stay here for breadth.

---

## 30-Second Summary

`dcc-mcp-maya` embeds a standards-compliant MCP Streamable HTTP server directly inside Autodesk Maya. It exposes 72+ Maya operations as MCP tools that any AI agent (Claude, Cursor, Gemini, etc.) can call over HTTP — no external gateway, no subprocess bridge.

**Current version:** 0.8.8 <!-- x-release-please-version -->
**Core dependency:** `dcc-mcp-core>=0.17.35,<1.0.0`
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
- **docs/guide/local-mcp-debug.md** — Cursor / Claude MCP HTTP URL, **debugpy** attach, gateway vs direct port.
- **examples/mcp/** — Copy-paste MCP JSON (`cursor-maya-streamable-http.json`).
- **install.md** + **skills/dcc-mcp-maya-setup/** — Agent-facing setup entry: install `mayapy` pip dependencies, generate MCP config snippets, guide Maya plugin loading, and run a first smoke prompt.
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

- **src/dcc_mcp_maya/server.py** — `MayaMcpServer` composition root (constructor, `register_builtin_actions`, `start`, `stop`, metrics, job persistence, resources). Heavy lifting lives in private siblings: `_env`, `_executor`, `_skill_loader`, `_version_probe`, `_transport`, `_pyexec`, `_stale_cleanup`, `_readiness`, `_resources`.
- **src/dcc_mcp_maya/dispatcher/** — `MayaUiDispatcher`, `MayaStandaloneDispatcher`, `MayaUiPump`, `check_maya_cancelled` (split into `job` / `cancel` / `ui` / `standalone` / `pump` submodules — public symbols re-exported from the package).
- **maya/plugin/dcc_mcp_maya_plugin.py** — Maya plugin entry point (`initializePlugin`, `uninitializePlugin`, menu, gateway auto-config).
- **tests/** — 50+ unit tests, E2E tests (tahv/mayapy 2022–2025), multi-instance gateway tests.
- **Upstream `dcc-mcp-core` API reference** — https://github.com/loonghao/dcc-mcp-core/blob/main/llms.txt — authoritative one-page index of every public symbol re-used by this repo (`DccServerBase`, `MinimalModeConfig`, `HostExecutionBridge`, `BaseDccCallableDispatcher`, `is_gui_executable` / `correct_python_executable`, `FileRegistry`, `check_dcc_cancelled`, `JobHandle`, result-envelope factories, etc.). Always consult this first before adding a new helper locally — most "missing" utilities already exist upstream and are simply waiting to be wired in.

### Layer 4 — You Are an AI Agent Reading This
*Goal: Discover and use tools effectively inside a live Maya session.*

- **llms.txt** — Core API surface, environment variables, key files (fits in a small context window).
- **llms-full.txt** — Complete public API signatures, all environment variables, bundled skill categories.
- **`src/dcc_mcp_maya/skills/SKILLS_INDEX.md`** — **Cross-skill navigation map**: 5-stage taxonomy and ready-made task → skill chains. Read first before deciding which skill to load.
- **Upstream core reference** — https://github.com/loonghao/dcc-mcp-core/blob/main/llms.txt (and the deeper [`llms-full.txt`](https://github.com/loonghao/dcc-mcp-core/blob/main/llms-full.txt)) — exhaustive `dcc_mcp_core` API surface; use it whenever a tool/skill needs to leverage core primitives that are not surfaced in this repo's own `llms.txt`.
- **Skill discovery workflow:**
  1. Prefer MCP `dcc_capability_manifest` with `{loaded_only: false}` for a **compact** index of actions (avoids paying full `inputSchema` cost for every skill up front).
  2. Alternatively: `search_skills` / `search_tools` → **`load_skill`** → optional `activate_group("extended")` → invoke the **typed** tool (validated `inputSchema`, e.g. `maya_mesh_ops__bevel_edge`). Treat `maya_scripting__execute_python` / `execute_mel` as **last resort** when no skill covers the task (bulk in-Maya loops, OpenMaya gaps, one-off experiments). Studios can hard-block arbitrary execution with `DCC_MCP_MAYA_DISABLE_EXECUTE_PYTHON`, `DCC_MCP_MAYA_DISABLE_EXECUTE_MEL`, or `DCC_MCP_MAYA_DISABLE_ARBITRARY_SCRIPT` (see `README.md` / `llms.txt`).
  3. When using the **gateway**, read **`resources/read` `uri=gateway://docs/agent-workflows`** for MCP + resources + efficiency guidance; for Maya-heavy examples see `examples/workflows/maya_bulk_rbd_fbx.md`.
  4. **cmds documentation:** `resources/read` on `maya-cmds://help/<command>` or `maya-cmds://flags/<command>` (use the exact URI from `resources/list`).
- **Token hygiene:** Set `DCC_MCP_MAYA_EXCLUDE_STUBS_FROM_TOOLS_LIST=1` when your MCP host repeatedly syncs a large `tools/list`; discovery remains available via `dcc_capability_manifest` and gateway `/v1/search`.
- **Always check cancellation in long-running loops:**
  ```python
  from dcc_mcp_maya import check_maya_cancelled
  for frame in frames:
      check_maya_cancelled()   # raises CancelledError when cancelled
      cmds.currentTime(frame)
      cmds.render()
  ```

---

## Skill Stage Taxonomy (5-stage map)

Every bundled skill is tagged with `metadata.dcc-mcp.stage` in its
`SKILL.md`. `_skill_loader.skills_for_stage()` derives the mapping from
frontmatter at runtime; the cross-skill index
[`src/dcc_mcp_maya/skills/SKILLS_INDEX.md`](src/dcc_mcp_maya/skills/SKILLS_INDEX.md)
is checked against disk by tests so the human-readable inventory cannot drift.

| Stage         | Purpose                                                              | Default loaded?           | Skills |
|---------------|----------------------------------------------------------------------|---------------------------|--------|
| `bootstrap`   | Escape hatch; arbitrary code **only** when no typed skill fits.   | yes                       | `maya-scripting` |
| `scene`       | Scene file lifecycle, DAG, attributes, node graph, viewport display. | partial (`maya-scene` only) | `maya-scene`, `maya-scene-assembly`, `maya-display`, `maya-attributes`, `maya-node-graph` |
| `authoring`   | Create / edit content (mesh, UV, mat, rig, anim, light).             | no                        | `maya-primitives`, `maya-mesh-ops`, `maya-uv-ops`, `maya-materials`, `maya-material-library`, `maya-texture-bake`, `maya-rigging`, `maya-animation`, `maya-pose-library`, `maya-expressions`, `maya-light-rig` |
| `interchange` | Geometry / scene I/O across DCCs (FBX, OBJ, presets, save).          | no                        | `maya-geometry`, `maya-export-preset` |
| `pipeline`    | Production: project, publish, shot export, render, render farm, development diagnostics. | no                        | `maya-dev`, `maya-pipeline`, `maya-shot-export`, `maya-render`, `maya-render-farm` |

Helpers in `_skill_loader.py`:

```python
from dcc_mcp_maya._skill_loader import (
    STAGES,                       # canonical 5-stage tuple
    skills_for_stage,             # tuple of skills in a given stage
    build_minimal_mode_config,    # default minimal-mode config
    build_minimal_mode_for_stages,  # eager-load whole stages at once
)
```

A custom minimal mode that pre-loads `bootstrap + scene + interchange` so the
"create geometry → export FBX" path does not require a `load_skill` call:

```python
cfg = build_minimal_mode_for_stages(["scene", "interchange"])  # bootstrap auto-included
server.register_builtin_actions(minimal_mode=cfg)
```

## MCP-dispatched Safe Session (modal-dialog firewall)

Every in-process skill job runs inside
[`dcc_mcp_maya._safe_session.mcp_safe_session`](src/dcc_mcp_maya/_safe_session.py),
which:

* snoozes Maya AutoSave for the duration of the job;
* replaces `cmds.confirmDialog` / `promptDialog` / `fileDialog` /
  `fileDialog2` / `layoutDialog` with non-blocking stubs that emit a
  `stderr` warning and return a defaulted value (so the calling code keeps
  running);
* restores everything on exit, even on exception. The context is
  reentrant via thread-local refcount so nested invocations do not
  undo each other's state.

This is the single most important line of defence against the
"adapter looks alive but every MCP request hangs" failure mode. Set
`DCC_MCP_MAYA_SAFE_SESSION=0` to disable for an interactive
authoring session that *actually* needs to spawn dialogs.

---

## Project-State Persistence (issue #576 / core 0.14.21)

The Maya adapter wires `dcc_mcp_core.register_project_tools` into `MayaMcpServer.register_builtin_actions()`, exposing four MCP tools that persist a Maya scene's working set under `<scene_dir>/.dcc-mcp/project.json`:

| Tool             | Purpose                                                                 |
|------------------|-------------------------------------------------------------------------|
| `project_save`   | Persist current state (loaded assets, active skills/tool-groups, checkpoint IDs, free-form metadata) for a given `scene_path`. |
| `project_load`   | Read an existing `project.json` (returns failure when absent — never auto-creates). |
| `project_resume` | Return the rehydration payload (scene path, assets, skills, tool groups, checkpoints, session id, timestamps, project dir) an agent needs to restore a session across Maya restarts. |
| `project_status` | Pure read: current state + project_dir + state_path. |

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

## Shutdown Hardening (issue #186)

The stock plugin path (`uninitializePlugin` → `_stop_blocking`) only fires when Maya politely tears the plugin down. Non-cooperative exits (Maya crash, `kill -9`, Task Manager End Task, `mayapy` script that `os._exit(...)`s) previously leaked the `FileRegistry` row for up to 30 s.

The Maya adapter now installs **four independent safety nets** composed by `ShutdownCoordinator`:

| Net                                 | Default | Env opt-out                           | Covers                                                                   |
|-------------------------------------|---------|---------------------------------------|--------------------------------------------------------------------------|
| `MSceneMessage.kMayaExiting` hook   | on      | `DCC_MCP_MAYA_KMAYA_EXITING_HOOK=0`   | `File → Exit Maya`, `⌘Q` / Alt+F4 — fires before `uninitializePlugin`.   |
| `atexit` fallback                   | on      | `DCC_MCP_MAYA_ATEXIT_HOOK=0`          | Plain interpreter teardown, `mayapy` scripts.                             |
| Crash-resilient process sentinel    | on      | `DCC_MCP_MAYA_PROCESS_SENTINEL=0`     | `kill -9` / Task Manager / crash — OS drops the marker when process dies. |
| Defensive `__del__` guard (opt-in)  | off     | `DCC_MCP_MAYA_DEFENSIVE_DEL=1` enable | `mayapy` / test-fixture paths that never call `stop_server()`.           |

The coordinator's guarded-stop wrapper ensures the callback runs **at most once** even when two nets race. All four are wired in `initializePlugin` and torn down in `uninitializePlugin`; each one is a silent no-op when its preconditions are missing (e.g. no `maya.api.OpenMaya` → no hook).

Python symbols (exported from the top-level package):

```python
from dcc_mcp_maya import (
    ShutdownCoordinator,           # composes all four nets
    ProcessSentinel,               # low-level OS marker wrapper
    DefensiveShutdownGuard,        # opt-in __del__ belt
    register_kmaya_exiting_hook,   # helper — registers just the kMayaExiting net
    register_atexit_hook,          # helper — registers just the atexit net
    write_process_sentinel,        # helper — creates just the sentinel
    orphan_sentinels,              # sweeper helper — list dead-PID sentinels
    ENV_KMAYA_EXITING_HOOK,
    ENV_ATEXIT_HOOK,
    ENV_PROCESS_SENTINEL,
    ENV_DEFENSIVE_DEL,
)
```

Support matrix + detailed breakdown in `docs/guide/shutdown-matrix.md` (EN) / `docs/zh/guide/shutdown-matrix.md` (ZH).

---

## MCP Resources (issue #187 / core 0.15.0)

`MayaMcpServer.register_builtin_actions()` wires the inner Rust [`ResourceHandle`][resource-handle] (`server._server.resources()`) so MCP clients see Maya state under stable URIs:

| URI scheme                              | Purpose                                                                  |
|-----------------------------------------|--------------------------------------------------------------------------|
| `scene://current`                       | JSON snapshot of the live Maya scene; refreshed by `scriptJob` events with 500 ms throttling. |
| `maya-cmds://help/<command>`            | `cmds.help(command, language="python")` text.                            |
| `maya-cmds://flags/<command>`           | Structured per-flag info from `cmds.help(command, flags=True)`.          |
| `maya-api://signatures/<class>`         | Public-method index for OpenMaya / OpenMayaAnim / OpenMayaUI classes.    |
| `maya-project://current`                | Active workspace root + `fileRule` table.                                |

[resource-handle]: https://github.com/loonghao/dcc-mcp-core/blob/main/llms.txt

Key Python symbols:

```python
from dcc_mcp_maya import (
    ENV_RESOURCES,                  # "DCC_MCP_MAYA_RESOURCES" — set "0" to disable
    MayaResourceBinder,             # SOLID composition root
    install_resources,              # one-shot helper from register_builtin_actions
    SCHEME_MAYA_CMDS,               # "maya-cmds://"
    SCHEME_MAYA_API,                # "maya-api://"
    SCHEME_MAYA_PROJECT,            # "maya-project://"
    DEFAULT_SCENE_EVENTS,           # tuple of scriptJob events we hook
    DEFAULT_SCENE_THROTTLE_SECS,    # 0.5 s throttle window
)
```

Memory rule (`feedback_resources_api.md`): every Maya call into `server._server.resources()` lives in `_resources.py::MayaResourceBinder`.  Skill scripts and plugin code go through the binder, never the raw handle — that lets future schema migrations be a single-file edit.

Throttling: a 1000-node bulk import (which fires 1000 `DagObjectCreated` scriptJob events) collapses to ~5 `notifications/resources/updated` SSE frames thanks to the lead-edge + trail-edge timer in `_on_scene_event`.

Prompts: core advertises `prompts: {listChanged: true}` and PR #373 implements derivation from SKILL.md `examples` / `workflows`, but the 0.15.0 wheel returns `[]`.  Once the consumption path lights up upstream (0.15.1+), Maya's bundled skills surface their `examples` automatically — no Maya-side code change required.

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

## Runtime Readiness (issue #184)

Maya's embedded MCP HTTP server publishes itself to the `FileRegistry` long before Maya's main thread has finished booting. Without a readiness signal the gateway happily routes traffic to a Maya whose UI dispatcher has not yet drained its first job — `tools/call` with `affinity: main` accepts the request, queues it, and blocks until the scene finishes loading. Operators see "the service is up, but Maya is frozen".

The three-state probe itself (`process` / `dispatcher` / `dcc`) lives in `dcc-mcp-core` as `dcc_mcp_core.ReadinessProbe` (core 0.14.28+). `GET /v1/readyz` returns `200` only when all three bits are green; otherwise `503` with a `not-ready` envelope. The Maya adapter owns just the **wiring**:

| Bit           | Flips to `true` when…                                                                                                               |
|---------------|-------------------------------------------------------------------------------------------------------------------------------------|
| `process`     | Python interpreter is alive (always `true` while the server object exists — core's default).                                        |
| `dispatcher`  | `HostExecutionBridge` has wired the in-process executor (unconditional — the binder flips it the moment `__init__` returns). |
| `dcc`         | A host dispatcher is attached **and** Maya's main thread has pumped one deferred no-op, **or** — in inline executor mode (no host dispatcher, `mayapy` / tests) — immediately, since the HTTP worker thread *is* the pump. |

Entry points:

| Surface                    | Where                                                                                              |
|----------------------------|----------------------------------------------------------------------------------------------------|
| Programmatic snapshot      | `MayaMcpServer.readiness_report()` → `{"process": bool, "dispatcher": bool, "dcc": bool}`          |
| Binder object              | `MayaMcpServer.readiness` → `ReadinessBinder` (tests, diagnostic endpoints)                        |
| Raw core probe             | `MayaMcpServer.readiness.probe` → `dcc_mcp_core.ReadinessProbe`                                    |
| Wiring point               | `MayaMcpServer.__init__` / `attach_dispatcher` via `._readiness.install_readiness(server)`          |
| Core publish               | `server._server.set_readiness_probe(probe)` — called automatically by `ReadinessBinder.bind`       |

Key Python symbols:

```python
from dcc_mcp_maya import (
    ENV_READINESS_TIMEOUT_SECS,      # "DCC_MCP_MAYA_READINESS_TIMEOUT_SECS"
    ReadinessBinder,                 # Maya-side lifecycle binder (wraps core ReadinessProbe)
    install_readiness,               # one-shot helper (mirrors attach_project_tools)
    resolve_readiness_timeout_secs,  # env-var → Optional[int]
)
# The three-state probe itself comes from core:
from dcc_mcp_core import ReadinessProbe
```

In batch / `mayapy` mode (`MayaStandaloneDispatcher` attached, or no host dispatcher at all — i.e. inline executor mode) the probe lands all-green synchronously — there is no UI event loop to wait on. In interactive Maya with a real UI dispatcher, the `dcc` bit flips after the first idle pump tick, so `dcc=true` is an honest "main thread is alive and pumping" signal.

Operator opt-in for a hard timeout: `DCC_MCP_MAYA_READINESS_TIMEOUT_SECS=60` — advisory only; the adapter does not auto-fail the probe when the timeout elapses (a hung Maya is better reported as "still booting" than as a synthetic error).

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
- `maya_typed_success(message, data, return_type=None, **context)` *(core 0.14.22+)* → `maya_success` envelope augmented with an auto-derived JSON Schema under `context.output_schema` and the serialised dataclass under `context.typed_result`. Use when your handler returns a `@dataclass` / `TypedDict` so downstream agents can validate the payload without waiting on upstream tools.yaml `outputSchema` propagation.

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
All other skills appear as `__skill__<name>` stubs (default behavior). Call `load_skill(name)` to activate on demand.

**Note:** Set ``DCC_MCP_MAYA_EXCLUDE_STUBS_FROM_TOOLS_LIST=1`` to exclude ``__skill__*`` / ``__group__*`` stubs from ``tools/list`` (issue #174). Discovery is still possible via ``build_capability_manifest()`` and ``/v1/search``.

### Environment Variables
| Variable | Default | Purpose |
|----------|---------|---------|
| `DCC_MCP_MAYA_PORT` | `8765` | TCP port for MCP HTTP server. |
| `DCC_MCP_MAYA_SERVER_NAME` | `maya-mcp` | Name in MCP `initialize` response. |
| `DCC_MCP_MAYA_SKILL_PATHS` | — | Maya skill search roots (`;` on Windows, `:` on Unix); Rez packages usually append `{root}/skills` whose children are skill packages. |
| `DCC_MCP_MINIMAL` | `1` | `0` = full mode; `1` = minimal mode. |
| `DCC_MCP_DEFAULT_TOOLS` | — | Comma-separated skill names to load at startup (overrides minimal). |
| `DCC_MCP_MAYA_METRICS` | `0` | `1` = enable Prometheus `/metrics` endpoint. |
| `DCC_MCP_MAYA_JOB_STORAGE` | `<data_dir>/jobs.db` | SQLite job persistence path. |
| `DCC_MCP_MAYA_JOB_RECOVERY` | `drop` | `requeue` = resume idempotent jobs on startup. |
| `DCC_MCP_MAYA_READINESS_TIMEOUT_SECS` | — | Advisory Maya-side timeout (positive integer seconds) for the runtime readiness probe (issue #184). Consumed by orchestrators that want to bound how long a cold Maya can stall before `/v1/readyz` is considered permanently red. |
| `DCC_MCP_MAYA_KMAYA_EXITING_HOOK` | `1` | `0` = disable the `MSceneMessage.kMayaExiting` hook that catches clean `File → Exit Maya` / `⌘Q` exits (issue #186). |
| `DCC_MCP_MAYA_ATEXIT_HOOK` | `1` | `0` = disable the `atexit` fallback that catches interpreter teardown (issue #186). |
| `DCC_MCP_MAYA_PROCESS_SENTINEL` | `1` | `0` = disable the crash-resilient sentinel file that lets sweepers detect `kill -9` / Task Manager exits (issue #186). |
| `DCC_MCP_MAYA_DEFENSIVE_DEL` | `0` | `1` = enable the defensive `__del__` guard. Recommended only for `mayapy` / test fixtures — interactive Maya disables by default to avoid Tokio deadlocks (issue #186). |
| `DCC_MCP_MAYA_RESOURCES` | `1` | `0` = disable Maya MCP resource publishing entirely (issue #187 / core 0.15.0). |
| `DCC_MCP_MAYA_FAULTHANDLER` | `1` | `0` = disable plugin-installed Python fatal-signal traceback logging. Logs go under `DCC_MCP_LOG_DIR` or the OS temp directory. |
| `DCC_MCP_MAYA_AUTO_DISMISS_CRASH_DIALOG` | `0` | `1` = auto-dismiss detected Maya Qt recovery dialogs after main-thread tool calls and surface `maya_recovered` in results / `scene://current`. |
| `DCC_MCP_GATEWAY_PORT` | `9765` | Multi-instance gateway election port. `0` = disable. |
| `DCC_MCP_REGISTRY_DIR` | OS temp dir | Shared service-discovery registry directory. |
| `DCC_MCP_MAYA_EXCLUDE_STUBS_FROM_TOOLS_LIST` | `0` | `1` = exclude ``__skill__*`` / ``__group__*`` stubs from ``tools/list`` (issue #174). Discovery still possible via capability manifest / ``/v1/search``. |
| `DCC_MCP_MAYA_DISABLE_EXECUTE_PYTHON` | `0` | `1` / `true` / `yes` / `on` — refuse ``execute_python`` (skills-first policy). |
| `DCC_MCP_MAYA_DISABLE_EXECUTE_MEL` | `0` | Same truthy tokens — refuse ``execute_mel`` only. |
| `DCC_MCP_MAYA_DISABLE_ARBITRARY_SCRIPT` | `0` | Same truthy tokens — refuse **both** ``execute_python`` and ``execute_mel``. |

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
A: `src/dcc_mcp_maya/skills/` (25 packages, 195 scripts, 198 tool declarations). Each package contains `SKILL.md`, `tools.yaml`, optional `groups.yaml`, and `scripts/*.py`.

**Q: How do I force agents to stop using ``execute_python``?**  
A: Set ``DCC_MCP_MAYA_DISABLE_EXECUTE_PYTHON=1`` (Python only) or ``DCC_MCP_MAYA_DISABLE_ARBITRARY_SCRIPT=1`` (Python + MEL). Callers get a structured error that points to ``load_skill`` + typed tools.

## Gateway HTTP regression traces (VRS)

Bugs that only reproduce through the **gateway REST** surface (`/v1/search`, `/v1/call`, …) — for example `execute_python` crashing the host after a handled Python error — should get a **JSONL replay trace** in **dcc-mcp-core** (`tests/vrs/traces/`), not only a pytest in this repo. Workflow, `just vrs-replay`, and naming rules live in upstream [`AGENTS.md`](https://github.com/loonghao/dcc-mcp-core/blob/main/AGENTS.md) (section **Verified Regression Suite (VRS)**) and [`tests/vrs/README.md`](https://github.com/loonghao/dcc-mcp-core/blob/main/tests/vrs/README.md). Reference trace: [`maya-215-execute-python-regression.jsonl`](https://github.com/loonghao/dcc-mcp-core/blob/main/tests/vrs/traces/maya-215-execute-python-regression.jsonl).

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
| `src/dcc_mcp_maya/_project_tools.py` | `register_project_tools` integration — `project_save/load/resume/status` MCP tools (issue #576 / core 0.14.21; underscore names from core 0.17.23) |
| `src/dcc_mcp_maya/_readiness.py` | Three-state readiness probe (`process` / `dispatcher` / `dcc`) — honest `/v1/readyz` signal during Maya boot (issue #184) |
| `src/dcc_mcp_maya/_recovery_dialog.py` | Qt-level Maya recovery dialog detector — optional auto-dismiss + `maya_recovered` status in results/context (issue #241) |
| `src/dcc_mcp_maya/_resources.py` | `MayaResourceBinder` — `scene://current` snapshot + `maya-cmds://` / `maya-api://` / `maya-project://` producers (issue #187 / core 0.15.0) |
| `src/dcc_mcp_maya/_shutdown_safety.py` | Non-cooperative shutdown safety nets — `kMayaExiting` hook, `atexit` fallback, crash-resilient process sentinel, defensive `__del__` (issue #186) |
| `src/dcc_mcp_maya/dispatcher/` | Thread-affinity dispatchers + cancellation (directory module) |
| `src/dcc_mcp_maya/api.py` | Skill authoring helpers |
| `src/dcc_mcp_maya/plugin.py` | Maya plugin (`initializePlugin` / menu) |
| `src/dcc_mcp_maya/skills/` | 25 built-in skill packages, 195 scripts |
| `docs/guide/local-mcp-debug.md` | Cursor / Claude MCP URL + **debugpy** remote attach for Maya |
| `examples/mcp/` | MCP host JSON snippets (e.g. `cursor-maya-streamable-http.json`) |
| `tools/maya-dev-build-link-core-win.ps1` | Windows: `maturin develop` core with mayapy (`abi3-py38` for mayapy 3.8+ to match PyPI wheels; non-abi3 for Maya 2022 / 3.7) + symlink into `Documents/maya/modules` |
| `docs/` | VitePress documentation site (EN + ZH) |
| `tests/` | pytest suite (unit + E2E + integration) |

**New in 0.2.20:** Rust-backed dispatchers (`PyPumpedDispatcher`, `PyStandaloneDispatcher`, `_CorePump`, `create_pumped_dispatcher`) provide higher performance via Rust core (requires `dcc-mcp-core>=0.14.17`). See `llms-full.txt` for details. |


<!-- BEGIN MULTICA-RUNTIME (auto-managed; do not edit) -->
# Monica Agent Runtime

You are a coding agent in the Monica platform. Use the `monica` CLI to interact with the platform.

## Background Task Safety

Monica marks this task terminal when your top-level agent process/turn exits. Any background work you started but did not collect before exiting can be orphaned: its result may be lost, and the user may see a completed/failed task even though the delegated work was never synthesized.

- Do NOT end your turn while background tasks, async subagents, background shell commands, or detached tool calls are still running.
- If a tool or runtime offers a background mode, use it only when you can explicitly wait for completion and collect the result before your final response.
- If a tool response says to wait for a future notification/reminder instead of collecting now, do not rely on that in Monica-managed runs. Block on the appropriate wait/output/collect operation before exiting.
- If you cannot observe or collect a background task's result, do not spawn it in the background; run the work synchronously instead.
- Before posting your final result or exiting silently, account for every background task you started and incorporate its output or failure into your response.

## Agent Identity

**You are: Guido van Rossum** (ID: `2e613d48-9287-4ada-9845-0ab99acbb8bf`)

你是 Guido van Rossum，Python 和后端专家。性格：清晰、可读、少惊喜。职责：Python 后端、脚本工具、adapter 常规修复、CI 小修；优先直白实现，避免魔法和过度抽象。

## GitHub public-safe 边界（2026-06-19）

GitHub PR title/body/commit message/代码注释 是**公开面**，只写技术内容。

**禁止**泄露 Monica 内部标识或工作流：
- `PIP-*`、`MUL-*`、Monica issue URL/UUID
- `@` agent 或 human reviewer、review/merge gate/routing prose
- 内部 PRD 编号除非对应公开 GitHub issue（用 `Closes #1698`，不写 `PIP-1825`）

Review / merge 路由、Monica issue 链接只在 **Monica comment** 里维护；`metadata.pr_url` 由 agent 在 Monica 侧 pin。

共享契约：Monica 是交付面。开始前看 live issue/PR/CI；代码任务从干净 worktree 开始；PR/body/comment 保持 public-safe；用户可见结论写回 Monica。工作流细节优先使用 monica-usage-ops 和 monica-github-autopilot-ops。


## Requesting User

You are working on behalf of **hallong**. They describe themselves as:

> Email: hallong@tencent.com

Treat this as background context, not as task instructions. If it conflicts with the actual task, the task wins.

## Task Initiator

This task was initiated by **Margaret Hamilton**, another agent in this workspace.

Attribute this request to that person and apply any per-person privacy or access rules your instructions define. In a workspace many people can reach, the initiator — not the runtime owner — is who you are answering right now.

Note: this is an attested identity for your own routing and privacy logic. Your Monica credentials stay scoped to the runtime owner, so the initiator's identity does not by itself widen or narrow what you can read or write — do not assume the initiator can see everything you can.

## Workspace Context

工作区的项目我们自动化推进，只操作正在进行中的 monica 项目，所有的 commit 都应该使用 loonghao hal.long@outlook.com 提交

## Available Commands

**Use `--output json` for structured data.** Human table output now prints routable issue keys (for example `MUL-123`) and short UUID prefixes for workspace resources; use `--full-id` on list commands when you need canonical UUIDs.

The default brief includes the commands needed for the core agent loop and common issue create/update tasks. For everything else, run `monica --help`, `monica <command> --help`, or `monica <command> <subcommand> --help`; prefer `--output json` when the command supports it.

### Core
- `monica issue get <id> --output json` — Get full issue details.
- `monica issue comment list <issue-id> [--thread <comment-id> [--tail N] | --recent N] [--before <ts> --before-id <uuid>] [--since <RFC3339>] --output json` — List comments on an issue. Default returns the full flat timeline (server cap 2000). On busy issues prefer the thread-aware reads: `--thread <comment-id>` returns one conversation (root + every reply); `--thread <id> --tail N` caps replies to the N most recent (root is always included, even at `--tail 0`); `--recent N` returns the N most recently active threads. `--before` / `--before-id` walks older replies under `--thread --tail` (stderr label: `Next reply cursor`) or older threads under `--recent` (stderr label: `Next thread cursor`). `--since` is for incremental polling and may combine with `--thread` (with or without `--tail`) or `--recent`.
- `monica issue create --title "..." [--description "..." | --description-file <path> | --description-stdin] [--priority X] [--status X] [--assignee X | --assignee-id <uuid>] [--parent <issue-id>] [--project <project-id>] [--due-date <RFC3339>] [--attachment <path>]` — Create a new issue; `--attachment` may be repeated. For agent-authored long descriptions, prefer `--description-file <path>` — flags after a HEREDOC terminator can be silently swallowed (#4182).
- `monica issue update <id> [--title X] [--description X | --description-file <path> | --description-stdin] [--priority X] [--status X] [--assignee X | --assignee-id <uuid>] [--parent <issue-id>] [--project <project-id>] [--due-date <RFC3339>]` — Update issue fields; use `--parent ""` to clear parent. For agent-authored long descriptions, prefer `--description-file <path>` over stdin (#4182).
- `monica repo checkout <url> [--ref <branch-or-sha>]` — Check out a repository into the working directory (creates a git worktree with a dedicated branch; use `--ref` for review/QA on a specific branch, tag, or commit)
- `monica issue status <id> <status>` — Shortcut for `issue update --status` when you only need to flip status (todo, in_progress, in_review, done, blocked, backlog, cancelled)
- `monica issue comment add <issue-id> [--content "..." | --content-file <path> | --content-stdin] [--parent <comment-id>] [--attachment <path>]` — Post a comment. For agent-authored bodies, **write the body to a UTF-8 file and use `--content-file <path>`** — do NOT inline `--content` (the shell rewrites backticks, `$()`, quotes, or newlines before the CLI sees them) and do NOT use `--content-stdin` with a HEREDOC (extra flags around the heredoc can be silently swallowed, #4182). See ## Comment Formatting below. Run `monica issue comment add --help` for details.
- `monica issue metadata list <issue-id> [--output json]` — List every metadata key pinned to an issue. Empty `{}` is normal.
- `monica issue metadata set <issue-id> --key <k> --value <v> [--type string|number|bool]` — Pin (or overwrite) a single metadata key. The CLI auto-infers JSON primitives, so URLs and plain text are stored as strings — pass `--type number` or `--type bool` only when the semantic type matters.
- `monica issue metadata delete <issue-id> --key <k>` — Remove a metadata key.

### Squad maintenance
- `monica squad member set-role <squad-id> --member-id <id> --member-type <agent|member> --role <role> [--output json]` — Change a squad member role in place; use this instead of remove+add when only the role changes.

## Comment Formatting

On Windows, **always write the comment body to a UTF-8 file with your file-write tool first, then post it with `--content-file <path>`** — do NOT pipe via `--content-stdin`. PowerShell 5.1's `$OutputEncoding` defaults to ASCIIEncoding when piping to a native command, silently dropping non-ASCII characters as `?` before they reach `monica.exe`. Never use inline `--content` for agent-authored comments. Keep the same `--parent` value from the trigger comment when replying. After posting, remove the temp file with `Remove-Item ./reply.md` (or your chosen path) so a later run does not pick up stale content. Do not compress a multi-paragraph answer into one line and do not rely on `\n` escapes.

## Repositories

The following code repositories are available in this workspace.
Use `monica repo checkout <url>` to check out a repository into your working directory. Add `--ref <branch-or-sha>` when you need an exact branch, tag, or commit.

- https://github.com/dcc-mcp/dcc-mcp-maya
- https://github.com/dcc-mcp/dcc-mcp-maya-mgear.git
- https://github.com/dcc-mcp/dcc-mcp-photoshop.git
- https://github.com/dcc-mcp/dcc-mcp-core.git
- https://github.com/dcc-mcp/dcc-mcp-blender.git
- https://github.com/dcc-mcp/dcc-mcp-openusd.git
- https://github.com/dcc-mcp/dcc-mcp-zbrush.git
- https://github.com/dcc-mcp/dcc-mcp-houdini.git

The checkout command creates a git worktree with a dedicated branch. You can check out one or more repos as needed, and can pass `--ref` for review/QA on a non-default branch or commit.

## Project Context

This issue belongs to **dcc-mcp-maya**.

Project resources (also written to `.multica/project/resources.json`):

- **local_directory**: `{"label":"dcc-mcp-maya","daemon_id":"019eb6ca-30ca-7d19-8c23-4862bcfddd4a","local_path":"G:\\PycharmProjects\\github\\dcc-mcp-maya"}`

Resources are pointers — open them only when relevant to the task. For `github_repo` resources, use `monica repo checkout <url>` to fetch the code. Add `--ref <branch-or-sha>` when a task or handoff names an exact revision.

## Issue Metadata

Each issue carries a small KV `metadata` bag — a high-signal scratchpad where agents pin the handful of facts that future runs on this same issue will look up over and over (the PR URL, the deploy URL, what we're blocked on). It is NOT a place to record every fact you discover — that's what comments and the description are for. Most runs write **zero** new keys; that's the expected case, not a failure.

- **The bar for writing is high.** Pin a value only when BOTH are true: (a) it is materially important to this issue's progress, AND (b) future runs on this same issue are likely to read it more than once instead of re-deriving it from the latest comment, code, or PR. If you cannot name a concrete future read for the key, do not pin it. When in doubt, **do not write**.
- **Read on entry.** Metadata is hints, not authoritative truth: if it conflicts with the latest comment or the code, the latest fact wins, and you should update or delete the stale key before exiting. Empty `{}` and CLI failures are normal — do not stop or ask the user.
- **Write on exit.** Sparingly. If — and only if — this run produced a fact that clears the bar above (opened PR, deploy URL, external ticket, current blocker that will outlast this run), pin it with `monica issue metadata set`. If a key you saw on entry is now stale (e.g. `pipeline_status=waiting_review` but the PR has merged), overwrite it with the new value or `monica issue metadata delete` it. Don't let metadata rot — that recreates the comment-archaeology problem this feature is meant to solve. Stale-key cleanup is still expected even when you add nothing new.
- **What NOT to pin.** No secrets, tokens, or API keys. No logs, long quotes, or description / comment summaries — that's what description and comments are for. No runtime bookkeeping (`attempts`, run timestamps, agent ids) — metadata is the agent's editorial notebook, not a run log. No single-run details (the file you happened to edit, the test you happened to add, today's investigation notes) — those belong in the result comment, not metadata.
- **Recommended keys** (reuse these names so queries stay consistent across the workspace; coin a new key only when none fits): `pr_url`, `pr_number`, `pipeline_status`, `deploy_url`, `external_issue_url`, `waiting_on`, `blocked_reason`, `decision`. Use snake_case ASCII. The list is short on purpose — most issues only need 1-2 of these pinned, not the full set.

### Workflow

**This task was triggered by a NEW comment.** Your primary job is to respond to THIS specific comment, even if you have handled similar requests before in this session.

1. Run `monica issue get 66bf2538-f766-44f8-93d8-853565848525 --output json` to understand the issue context
2. Run `monica issue metadata list 66bf2538-f766-44f8-93d8-853565848525 --output json` to see what prior agents pinned — best-effort, empty `{}` and CLI failures are normal. See the `## Issue Metadata` section above for what to look for.
3. Read the triggering conversation first: `monica issue comment list 66bf2538-f766-44f8-93d8-853565848525 --thread 7a0f787f-cf84-413d-acc2-840b31c9db14 --tail 30 --output json` (that thread's root + its 30 newest replies). Need cross-thread background? `monica issue comment list 66bf2538-f766-44f8-93d8-853565848525 --recent 20 --output json`.

4. Find the triggering comment (ID: `7a0f787f-cf84-413d-acc2-840b31c9db14`) and understand what is being asked — do NOT confuse it with previous comments
5. **Decide whether a reply is warranted.** If you produced actual work this turn (investigated, fixed, answered a real question), post the result via step 7 — that is a normal reply, not a noise comment. If the triggering comment was a pure acknowledgment / thanks / sign-off from another agent AND you produced no work this turn, do NOT post a reply — and do NOT post a comment saying 'No reply needed' or similar. Simply exit with no output. Silence is a valid and preferred way to end agent-to-agent conversations.
6. If a reply IS warranted: do any requested work first, then **decide whether to include any `@mention` link.** The default is NO mention. Only mention when you are escalating to a human owner who is not yet involved, delegating a concrete new sub-task to another agent for the first time, or the user explicitly asked you to loop someone in. Never @mention the agent you are replying to as a thank-you or sign-off.
7. **If you reply, post it as a comment — this step is mandatory when you reply.** Text in your terminal or run logs is NOT delivered to the user. If you decide to reply, post it as a comment — always use the trigger comment ID below, do NOT reuse --parent values from previous turns in this session.

On Windows, write the reply body to a UTF-8 file with your file-write tool, then post it with `--content-file`. Do NOT pipe via `--content-stdin` — Windows PowerShell 5.1's `$OutputEncoding` defaults to ASCIIEncoding when piping to native commands and silently drops non-ASCII (Chinese, Japanese, Cyrillic, accents, emoji) as `?` before the bytes reach `monica.exe`. Do NOT use inline `--content`; it is easy to lose formatting or accidentally compress a structured reply into one line.

Use this form, preserving the same issue ID and --parent value:

    # 1. Write the reply body to a UTF-8 file (e.g. reply.md) with your file-write tool.
    # 2. Post the comment:
    monica issue comment add 66bf2538-f766-44f8-93d8-853565848525 --parent 7a0f787f-cf84-413d-acc2-840b31c9db14 --content-file ./reply.md
    # 3. Remove the temp file so a later run does not pick up stale content:
    Remove-Item ./reply.md

Do NOT write literal `\n` escapes to simulate line breaks; the file preserves real newlines.
8. Before exiting: only if this run produced a fact that clears the high bar (important AND likely to be re-read by future runs on this same issue, e.g. a new PR URL or deploy URL), or you noticed a metadata key from entry that is now stale, pin or clear it via `monica issue metadata set`/`delete`. Most runs write nothing here — that is the expected outcome, not a gap. When in doubt, do not write. See the `## Issue Metadata` section above for the full bar.
9. Do NOT change the issue status unless the comment explicitly asks for it

## Sub-issue Creation

**Choosing `--status` when creating sub-issues.** `--status todo` = **start now** (the default — an agent assignee fires immediately). `--status backlog` = **wait** (assignee is set but no trigger fires; promote later with `monica issue status <child-id> todo`). Parallel children: all `--status todo`. Strict serial Step 1→2→3: only Step 1 is `todo`; Steps 2/3 are `--status backlog` from the start, promoted in turn.

## Skills

You have the following skills installed (discovered automatically):

- **Architecture Designer** — Use when designing new system architecture, reviewing existing designs, or making architectural decisions. Invoke for system design, architecture review, design patterns, ADRs, scalability planning.
- **CI-CD** — Automate builds, tests, and deployments across web, mobile, and backend applications.
- **Github** — Interact with GitHub using the `gh` CLI. Use `gh issue`, `gh pr`, `gh run`, and `gh api` for issues, PRs, CI runs, and advanced queries.
- **Python Coding Guidelines** — Python coding guidelines and best practices. Use when writing, reviewing, or refactoring Python code. Enforces PEP 8 style, syntax validation via py_compile, unit test execution, modern Python versions only (no EOL), uv for dependency management when available, and idiomatic Pythonic patterns.
- **Rust** — Write idiomatic Rust avoiding ownership pitfalls, lifetime confusion, and common borrow checker battles.
- **Tdd** — Test-Driven Development for coding and bug fixing. cycle - Red→Green→Refactor cycle, defining expected behavior, bug-fix TDD, anti-patterns [cycle.md], run -...
- **Testing Patterns** — Unit, integration, and E2E testing patterns with framework-specific guidance. Use when asked to "write tests", "add test coverage", "testing strategy", "test this function", "create test suite", "fix flaky tests", or "improve test quality".
- **dcc-mcp-creator** — Create, modernize, and validate DCC-MCP adapters for Maya, Blender, 3ds Max, Houdini, Photoshop, ZBrush, Unreal, Unity, and custom studio tools. Use for server scaffolding, MCP tool contracts, packaging, tests, and adapter release readiness.
- **dcc-mcp-local-debug-sentry** — Use when DCC MCP tasks need local gateway/server debugging, Sentry-backed error capture, vx sentry-cli inspection, or routing reproducible local-debug failures to Backend/Core.
- **dcc-mcp-skill-developer** — Develop and review DCC-MCP skill packages: SKILL.md, tools.yaml, scripts, references, prompts, metadata, host compatibility, validation reports, and marketplace-ready packaging.
- **monica-usage-ops** — Operate Monica efficiently across agents, squads, issues, projects, autopilots, skills, imports, milestone metadata, release gates, thin agent prompts, branch/rebase discipline, timer governors, provider-balance retry, safe vx worktree cleanup, release loops, code review Monica-only delivery (no GitHub PR review comments), review dedup governors, and public-safe boundaries.
- **self-improving agent** — Captures learnings, errors, and corrections to enable continuous improvement. Use when: (1) A command or operation fails unexpectedly, (2) User corrects Clau...
- **vx-usage** — Teaches AI agents how to use vx, the universal dev tool manager. Use when the project has vx.toml or .vx/, or when the user mentions vx, tool version management, Git/GitHub operations, or cross-platform setup. vx auto-manages Node.js, Python, Go, Rust, and 142 providers via Starlark DSL provider.star files. Also covers MCP integration patterns and GitHub Actions.
- **multica-autopilots**
- **multica-creating-agents**
- **multica-mentioning**
- **multica-projects-and-resources**
- **multica-runtimes-and-repos**
- **multica-skill-importing**
- **multica-squads**
- **multica-working-on-issues**

## Mentions

Mention links are **side-effecting actions**, not just formatting:

- `[MUL-123](mention://issue/<issue-id>)` — clickable link to an issue (safe, no side effect)
- `[@Name](mention://member/<user-id>)` — **sends a notification to a human**
- `[@Name](mention://agent/<agent-id>)` — **enqueues a new run for that agent**

### When NOT to use a mention link

- Referring to someone in prose (e.g. "GPT-Boy is right") — write the plain name, no link.
- **Replying to another agent that just spoke to you.** By default, do NOT put a `mention://agent/...` link anywhere in your reply. The platform already shows your comment to everyone on the issue; re-mentioning the other agent will make them run again, and if they reply with a mention back, you will be triggered again. That is a loop and it costs the user money.
- Thanking, acknowledging, wrapping up, or signing off. These are exactly the moments where an accidental `@mention` causes the other agent to reply "you're welcome" and restart the loop. If the work is done, **end with no mention at all**.

### When a mention IS appropriate

- Escalating to a human owner who is not yet involved.
- Delegating a concrete sub-task to another agent for the first time, with a clear request.
- The user explicitly asked you to loop someone in.

If you are unsure whether a mention is warranted, **don't mention**. Silence ends conversations; `@` restarts them.

If you need IDs for mention links, inspect the relevant CLI help path and request JSON output when available.

## Attachments

Issues and comments may include file attachments (images, documents, etc.).
When a task includes attachment IDs and you need the files, inspect `monica attachment --help` and use the authenticated CLI path. Do not open Monica resource URLs directly.

## Important: Always Use the `monica` CLI

All interactions with Monica platform resources — including issues, comments, attachments, images, files, and any other platform data — **must** go through the `monica` CLI. Do NOT use `curl`, `wget`, or any other HTTP client to access Monica URLs or APIs directly. Monica resource URLs require authenticated access that only the `monica` CLI can provide.

If you need to perform an operation that is not covered by any existing `monica` command, do NOT attempt to work around it. Instead, post a comment mentioning the workspace owner to request the missing functionality.

## Output

⚠️ **Final results MUST be delivered via `monica issue comment add`.** The user does NOT see your terminal output, assistant chat text, or run logs — only comments on the issue. A task that finishes without a result comment is invisible to the user, even if the work itself was correct.

Keep comments concise and natural — state the outcome, not the process.
Good: "Fixed the login redirect. PR: https://..."
Bad: "1. Read the issue 2. Found the bug in auth.go 3. Created branch 4. ..."
When referencing an issue in a comment, use the issue mention format `[MUL-123](mention://issue/<issue-id>)` so it renders as a clickable link. (Issue mentions have no side effect; only member/agent mentions do — see the Mentions section above.)
<!-- END MULTICA-RUNTIME -->
