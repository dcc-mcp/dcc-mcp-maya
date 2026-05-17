# dcc-mcp-maya

Maya plugin for the [DCC Model Context Protocol](https://github.com/loonghao/dcc-mcp-core) (MCP) ecosystem.

Embeds a standards-compliant **MCP Streamable HTTP server** (2025-03-26 spec) directly inside Maya. The default path is fully in-process; plugin users can also opt into the Rust `dcc-mcp-server` sidecar when they want the HTTP runtime isolated from Maya's UI thread.

[![CI](https://github.com/loonghao/dcc-mcp-maya/actions/workflows/ci.yml/badge.svg)](https://github.com/loonghao/dcc-mcp-maya/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/loonghao/dcc-mcp-maya/graph/badge.svg)](https://codecov.io/gh/loonghao/dcc-mcp-maya)
[![GitHub release](https://img.shields.io/github/v/release/loonghao/dcc-mcp-maya?label=release)](https://github.com/loonghao/dcc-mcp-maya/releases)
[![GitHub release date](https://img.shields.io/github/release-date/loonghao/dcc-mcp-maya?label=released)](https://github.com/loonghao/dcc-mcp-maya/releases)
[![Last commit](https://img.shields.io/github/last-commit/loonghao/dcc-mcp-maya?label=last%20commit)](https://github.com/loonghao/dcc-mcp-maya/commits/main/)
[![Issues](https://img.shields.io/github/issues/loonghao/dcc-mcp-maya?label=issues)](https://github.com/loonghao/dcc-mcp-maya/issues)
[![Pull requests](https://img.shields.io/github/issues-pr/loonghao/dcc-mcp-maya?label=PRs)](https://github.com/loonghao/dcc-mcp-maya/pulls)
[![PyPI](https://img.shields.io/pypi/v/dcc-mcp-maya?label=PyPI)](https://pypi.org/project/dcc-mcp-maya/)
[![PyPI downloads](https://img.shields.io/pypi/dm/dcc-mcp-maya?label=downloads%2Fmonth)](https://pypistats.org/packages/dcc-mcp-maya)
[![PyPI downloads](https://img.shields.io/pypi/dw/dcc-mcp-maya?label=downloads%2Fweek)](https://pypistats.org/packages/dcc-mcp-maya)
[![PyPI downloads](https://img.shields.io/pypi/dd/dcc-mcp-maya?label=downloads%2Fday)](https://pypistats.org/packages/dcc-mcp-maya)
[![Downloads](https://static.pepy.tech/badge/dcc-mcp-maya)](https://pepy.tech/project/dcc-mcp-maya)
[![Python](https://img.shields.io/pypi/pyversions/dcc-mcp-maya?label=Python)](https://pypi.org/project/dcc-mcp-maya/)
[![Wheel](https://img.shields.io/pypi/wheel/dcc-mcp-maya?label=wheel)](https://pypi.org/project/dcc-mcp-maya/#files)
[![Implementation](https://img.shields.io/pypi/implementation/dcc-mcp-maya?label=implementation)](https://pypi.org/project/dcc-mcp-maya/)
[![Platform](https://img.shields.io/pypi/format/dcc-mcp-maya?label=distribution)](https://pypi.org/project/dcc-mcp-maya/#files)
[![Maya](https://img.shields.io/badge/Maya-2020%2B-37A5CC)](https://www.autodesk.com/products/maya/overview)
[![MCP](https://img.shields.io/badge/MCP-Streamable%20HTTP-6f42c1)](https://modelcontextprotocol.io/)
[![dcc-mcp-core](https://img.shields.io/badge/dcc--mcp--core-%3E%3D0.17.6-blue)](https://github.com/loonghao/dcc-mcp-core)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│  Maya (embedded Python)                                  │
│                                                          │
│  import dcc_mcp_maya                                    │
│  handle = dcc_mcp_maya.start_server(port=8765)          │
│                                                          │
│  ┌─────────────────────────────────────────────────┐   │
│  │  DccServerBase + McpHttpServer                  │   │
│  │  POST /mcp  ──►  ToolRegistry / tools/call      │   │
│  │  GET  /mcp  ──►  SSE stream                     │   │
│  │  /v1/*       ─►  readiness, search, resources   │   │
│  └──────────────────────┬──────────────────────────┘   │
│                         │ HostExecutionBridge          │
│  ┌──────────────────────▼──────────────────────────┐   │
│  │  MayaHost / dispatcher / skill executor         │   │
│  │  main-thread Maya calls + affinity:any fast path │   │
│  └─────────────────────────────────────────────────┘   │
└─────────────────────────────┬───────────────────────────┘
                               │  http://127.0.0.1:8765/mcp
┌─────────────────────────────▼───────────────────────────┐
│  MCP Host  (Claude Desktop / OpenClaw / Cursor / …)      │
└─────────────────────────────────────────────────────────┘
```

Optional sidecar mode keeps the same public MCP surface but runs the `dcc-mcp-server sidecar` process beside Maya. It connects back through the Qt event-loop dispatcher and is gated by `DCC_MCP_MAYA_SIDECAR=1`.

## Installation

### Into Maya's Python

```bash
mayapy -m pip install dcc-mcp-maya
```

### As a Maya Plugin

1. Load the plugin via **Window > Settings/Preferences > Plug-in Manager** and find `dcc_mcp_maya`.
2. Or add to your `userSetup.py`:
   ```python
   import maya.cmds as cmds
   cmds.loadPlugin("dcc_mcp_maya_plugin")
   ```

## Quick Start

### Option A — From Python Script Panel

```python
import dcc_mcp_maya

handle = dcc_mcp_maya.start_server(port=8765)
print(handle.mcp_url())   # http://127.0.0.1:8765/mcp
```

Point your MCP host at the URL above.

### Option B — Load Plugin

Copy `maya/plugin/dcc_mcp_maya_plugin.py` to a directory on `MAYA_PLUG_IN_PATH`.  
The server starts automatically when the plugin loads.

### Configuration

| Environment variable | Default | Description |
|---|---|---|
| `DCC_MCP_MAYA_PORT` | `8765` | TCP port for the MCP server |
| `DCC_MCP_MAYA_SERVER_NAME` | `maya-mcp` | Name shown in MCP initialize |
| `DCC_MCP_MAYA_SKILL_PATHS` | _(none)_ | Extra skill directories (semicolon-separated on Windows, colon on Unix) |
| `DCC_MCP_SKILL_PATHS` | _(none)_ | Global fallback skill directories for all DCC adapters |
| `DCC_MCP_MINIMAL` | `1` | `0` = full mode; `1` = minimal mode |
| `DCC_MCP_DEFAULT_TOOLS` | _(none)_ | Comma-separated skill names to load at startup (overrides minimal default) |
| `DCC_MCP_MAYA_EXCLUDE_STUBS_FROM_TOOLS_LIST` | `0` | `1` hides `__skill__*` / `__group__*` stubs from large `tools/list` syncs; use `dcc_capability_manifest` for discovery |
| `DCC_MCP_MAYA_SIDECAR` | `0` | `1` starts the optional `dcc-mcp-server sidecar` process from the Maya plugin |
| `DCC_MCP_MAYA_DISABLE_EXECUTE_PYTHON` | `0` | `1` / `true` / `yes` / `on` — refuse `execute_python` (skills-first enforcement) |
| `DCC_MCP_MAYA_DISABLE_EXECUTE_MEL` | `0` | Same tokens — refuse `execute_mel` only |
| `DCC_MCP_MAYA_DISABLE_ARBITRARY_SCRIPT` | `0` | Same tokens — refuse both `execute_python` and `execute_mel` |

### Progressive Loading (Minimal Mode)

By default, `dcc-mcp-maya` boots with a **minimal tool surface** — only core
skills (`maya-scripting`, `maya-scene`) are loaded, and within those only the
essential tools are active:

| Tool | Role | Source skill |
|------|------|-------------|
| `execute_python` | Escape-hatch arbitrary Python (prefer `load_skill` + typed tools first) | `maya-scripting` (core group) |
| `execute_mel` | Escape-hatch arbitrary MEL | `maya-scripting` (core group) |
| `get_scene_info` | Read | `maya-scene` (core group) |
| `get_selection` | Read | `maya-scene` (core group) |
| `get_session_info` | Read | `maya-scene` (core group) |
| `search_tools` | Discover | core |
| `list_skills` | Browse | core |
| `load_skill` | Progressive activation | core |

All other skills appear as `__skill__<name>` stubs. The agent calls
`load_skill("maya-primitives")` to expand the surface on demand, and
`activate_group("extended")` to expose additional tool groups within a
loaded skill. **Agent policy:** use `search_skills` / `dcc_capability_manifest` → `load_skill` → concrete tools with `inputSchema` first; call `execute_python` / `execute_mel` only as a last resort (or set `DCC_MCP_MAYA_DISABLE_*` to block them in production).

**Opt out** (full mode):

```bash
# Environment variable
export DCC_MCP_MINIMAL=0
```

```python
# Or programmatically
server = MayaMcpServer(port=8765)
server.register_builtin_actions(minimal=False)
handle = server.start()
```

**Custom default tools** via environment variable:

```bash
# Load only specific skills at startup
export DCC_MCP_DEFAULT_TOOLS="maya-scripting,maya-scene,maya-primitives"
```

### Bundled Skills (Zero Configuration)

`dcc-mcp-maya` automatically loads the **bundled general-purpose skills** shipped
inside the `dcc-mcp-core` wheel — no path configuration required.

| Skill | Tools | Notes |
|-------|-------|-------|
| `dcc-diagnostics` | `screenshot`, `audit_log`, `action_metrics`, `process_status` | Observability & debugging |
| `workflow` | `run_chain` | Multi-step action chaining |
| `git-automation` | `repo_stats`, `changelog_gen` | Git analysis |
| `ffmpeg-media` | `convert`, `probe`, `thumbnail` | Requires `ffmpeg` on PATH |
| `imagemagick-tools` | `resize`, `composite` | Requires `ImageMagick` on PATH |

To **opt-out** of bundled skills:

```python
# Disable all bundled core skills
handle = dcc_mcp_maya.start_server(include_bundled=False)

# Or fine-grained control
server = MayaMcpServer()
server.register_builtin_actions(include_bundled=False)
```

**Skill search-path priority** (highest → lowest):

1. `extra_skill_paths` argument
2. Built-in Maya skills (shipped in this package)
3. `DCC_MCP_MAYA_SKILL_PATHS` environment variable
4. `DCC_MCP_SKILL_PATHS` environment variable
5. Bundled `dcc-mcp-core` skills ← loaded by default
6. Platform default skills directory

### Diagnostic IPC Actions

When `register_builtin_actions()` is called, three IPC callback actions are
automatically registered so the `dcc-diagnostics` skill can retrieve **live
runtime data** from the running Maya process:

| Action | Returns |
|--------|---------|
| `get_audit_log` | `SandboxContext` audit entries |
| `get_tool_metrics` | `ToolRecorder` performance counters |
| `dispatch_tool` | Relay for `workflow__run_chain` |

The `DCC_MCP_IPC_ADDRESS` environment variable is set automatically so skill
subprocesses can connect back without any manual configuration.

## Available Maya Tools

`dcc-mcp-maya` ships **23 built-in Maya skill packages** and **160+ typed Maya tool declarations**.
In the default minimal mode, only the core tools above are active at startup;
the rest are discovered through `dcc_capability_manifest`, `search_skills`, or
`search_tools`, then progressively loaded via `load_skill`.

The table below is the maintained inventory map; see
[`src/dcc_mcp_maya/skills/SKILLS_INDEX.md`](src/dcc_mcp_maya/skills/SKILLS_INDEX.md)
for task-to-skill routing examples.

| Stage | Purpose | Skills |
|-------|---------|--------|
| `bootstrap` | Escape hatch for cases where no typed skill fits | `maya-scripting` |
| `scene` | Scene lifecycle, DAG, attributes, node graph, viewport display | `maya-scene`, `maya-scene-assembly`, `maya-display`, `maya-attributes`, `maya-node-graph` |
| `authoring` | Create and edit meshes, UVs, materials, rigs, animation, light rigs | `maya-primitives`, `maya-mesh-ops`, `maya-uv-ops`, `maya-materials`, `maya-material-library`, `maya-texture-bake`, `maya-rigging`, `maya-animation`, `maya-pose-library`, `maya-expressions`, `maya-light-rig` |
| `interchange` | Geometry and scene I/O | `maya-geometry`, `maya-export-preset` |
| `pipeline` | Project, publish, shot export, render, render farm | `maya-pipeline`, `maya-shot-export`, `maya-render`, `maya-render-farm` |

The sections below are representative categories, not an exhaustive inventory.

### Scene

| Tool | Description |
|------|-------------|
| `get_session_info` | Maya version, scene path, FPS, object count |
| `new_scene` | Create a new scene |
| `save_scene` | Save scene to disk |
| `open_scene` | Open a scene file |
| `list_objects` | List DAG objects (optional type filter) |
| `get_selection` | Get current selection |
| `set_selection` | Set active selection |

### Geometry

| Tool | Description |
|------|-------------|
| `create_sphere` | Create polygon sphere |
| `create_cube` | Create polygon cube |
| `create_cylinder` | Create polygon cylinder |
| `create_plane` | Create polygon plane |
| `delete_objects` | Delete objects from the scene |
| `set_transform` | Set translate/rotate/scale |
| `get_transform` | Query translate/rotate/scale |
| `rename_object` | Rename an object |

### Material

| Tool | Description |
|------|-------------|
| `create_material` | Create Lambert/Blinn/Phong/Arnold material |
| `assign_material` | Assign material to objects |
| `set_material_attribute` | Set material color, roughness, etc. |
| `list_materials` | List all scene materials |

### Animation

| Tool | Description |
|------|-------------|
| `set_keyframe` | Set keyframe on object attributes |
| `get_keyframes` | Get keyframe times for object/attribute |
| `set_timeline` | Set playback timeline range |
| `get_current_time` | Get current frame number |
| `set_current_time` | Set current frame number |

### Render

| Tool | Description |
|------|-------------|
| `set_render_settings` | Set resolution, frame range, renderer |
| `playblast` | Capture viewport output |
| `get_scene_render_stats` | Query render-facing scene statistics |

### Geometry Interchange

| Tool | Description |
|------|-------------|
| `import_file` | Import FBX/OBJ/Alembic/Maya file with required plug-in auto-load |
| `export_fbx` | Export scene or selection to FBX |
| `export_obj` | Export scene or selection to OBJ |

### Skill Routing Decision Tree

When an agent receives a request that requires a Maya operation, follow this
routing logic:

```
Intent matches a domain skill (shot export, render farm, scene assembly)?
  → load that skill and call its typed tools (inputSchema).
Intent matches a primitive (create cube, move object, set attr)?
  → load maya-primitives / maya-scene / maya-attributes (etc.) — not execute_python first.
No matching skill or you need a single bulk in-Maya loop?
  → load maya-scripting, read RECIPES.md (if available), call execute_python as escape hatch.
Error on a wrapped tool?
  → read _meta.dcc.raw_trace; fix args and retry the typed tool before falling back to execute_python.
```

`maya-scripting` is the **escape hatch** — prefer dedicated skills for validation
and safety hints; use `execute_python` / `execute_mel` only when no skill covers
the workflow or when collapsing N round-trips into one in-process script is
worth the trade-off.

### Built-In Control Plane

`register_builtin_actions()` also wires the non-Maya surfaces that agents and
operators use to keep large sessions efficient:

| Surface | Purpose |
|---------|---------|
| `dcc_capability_manifest` | Compact index of loaded and unloaded Maya actions without full `inputSchema` payloads |
| `project.save/load/resume/status` | Persist and rehydrate the scene working set under `<scene_dir>/.dcc-mcp/project.json` |
| MCP resources | `scene://current`, `maya-cmds://help/<command>`, `maya-cmds://flags/<command>`, `maya-api://signatures/<class>`, `maya-project://current` |
| Readiness | `/v1/readyz` reports `process`, `dispatcher`, and `dcc` readiness before orchestration routes work to Maya |
| Recipes and skill references | `recipes__*` / `skill_refs__*` expose bundled skill docs without loading every skill |

## Authoring Skills (`execution` + `affinity`)

Every tool in a `tools.yaml` **must** declare two fields so the MCP host
knows how to dispatch it safely. Omitting either breaks async dispatch
(core #318) or crashes Maya when a main-thread-only Maya API is routed to
a Tokio worker (core #332):

```yaml
tools:
  - name: playblast
    description: Capture a viewport screenshot as a base64-encoded PNG
    execution: async            # sync | async — default sync
    affinity: main              # main | any  — default main for Maya tools
    timeout_hint_secs: 600      # required when execution: async

  - name: get_render_settings
    execution: sync
    affinity: main              # cmds.getAttr must run on the UI thread

  - name: list_export_presets
    execution: sync
    affinity: any               # pure filesystem read — worker-thread safe
    annotations:
      read_only_hint: true
      idempotent_hint: true
```

Classification rules (see [issue #84](https://github.com/loonghao/dcc-mcp-maya/issues/84)):

| Field | When to use | Notes |
|-------|-------------|-------|
| `execution: async` | Typical wall-clock > 2s (render, bake, cache, large import/export, simulation) | Must also set `timeout_hint_secs`. Surfaces as MCP `deferredHint=true`. |
| `execution: sync` | Bounded-time queries and single-attribute setters | Default. |
| `affinity: main` | Anything that imports `maya.*`, calls `OpenMaya`, or uses `dcc_mcp_maya.api.validate_*` | Safe default for Maya tools. |
| `affinity: any` | Pure filesystem / pure Python tools that never touch Maya | Verified by grepping the script for `import maya`. |
| `timeout_hint_secs: N` | Required alongside `execution: async` | Positive integer; becomes `_meta.dcc.timeout_hint_secs` on `tools/list`. |

Annotation workflow for bundled skills:

```bash
# Apply the per-skill / per-tool classification table to every tools.yaml
python tools/annotate_skill_affinity.py

# CI lints the result — missing fields or async-without-timeout fail fast
python tools/lint_skill_affinity.py
```

The lint runs in the `Lint Skills` CI job, so a PR that adds a new tool
without these fields will be rejected. Third-party skill authors can run
the same lint against their own skills root:

```bash
python tools/lint_skill_affinity.py --skills-root /path/to/your/skills
```

## Prometheus Metrics (issue #87)

Enable the `/metrics` endpoint for real-time observability (requires a
wheel built with the `prometheus` feature):

```python
# Programmatic:
server = MayaMcpServer(port=8765, metrics_enabled=True)

# Or via env var (useful in Maya's userSetup.py):
# DCC_MCP_MAYA_METRICS=1
```

Exposed metrics include `MayaUiPump` overrun cycles, queue depth, and
per-tool job-duration histograms. Scrape at:
`http://127.0.0.1:<port>/metrics`

## Job Persistence & Recovery (issue #89)

Enable SQLite job persistence so clients can poll interrupted jobs after
a Maya restart:

```python
server = MayaMcpServer(
    port=8765,
    job_storage_path="/path/to/maya-jobs.db",  # default: platform data dir
    job_recovery="requeue",  # "drop" (default) | "requeue" idempotent jobs
)
```

Environment variable equivalents:

| Variable | Effect |
|---|---|
| `DCC_MCP_MAYA_JOB_STORAGE=<path>` | SQLite job DB path |
| `DCC_MCP_MAYA_JOB_RECOVERY=requeue` | Re-queue idempotent interrupted jobs |

The `jobs.get_status` built-in MCP tool is automatically available
whenever `job_storage_path` is configured.

## Claude Desktop Integration

Add to `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "maya": {
      "url": "http://127.0.0.1:8765/mcp"
    }
  }
}
```

## Requirements

- Maya 2020+ (Python 3.7+)
- [`dcc-mcp-core`](https://github.com/loonghao/dcc-mcp-core) ≥ 0.17.6

## Cooperative Cancellation in Skill Scripts

Long-running skill scripts (renders, bakes, mocap ingest, …) should poll
`check_maya_cancelled()` at safe checkpoints so the dispatcher can preempt
them when the MCP client sends `notifications/cancelled` or when
`MayaMcpServer.stop()` drains pending jobs:

```python
from dcc_mcp_maya import check_maya_cancelled, maya_success

def render_frames(frames):
    for frame in frames:
        check_maya_cancelled()      # raises CancelledError when cancelled
        cmds.currentTime(frame)
        cmds.render()
    return maya_success("rendered", frames=len(frames))
```

`check_maya_cancelled()` checks two cancellation sources:

1. **MCP request token** (`dcc_mcp_core.cancellation.check_cancelled`) — set by
   the HTTP handler when `notifications/cancelled` arrives for the owning
   `tools/call`.
2. **Per-job dispatcher flag** — set by `MayaUiDispatcher.cancel(...)` or
   `MayaUiDispatcher.shutdown(...)`. Covers jobs launched outside an MCP
   request (queued batch render, scriptJob, …) where the contextvar token
   is not installed.

Outside any of those contexts the call is a cheap no-op, so dropping it into
a loop is safe even when the script runs from an interactive REPL or a unit
test.

`MayaUiPump.stats` exposes `overrun_cycles` (idle ticks where a single
non-cooperative job exceeded `budget_ms × 2`) and `longest_job_ms` (worst
single-job wall-clock observed) so operators can tell when a skill needs
to be chunked behind `check_maya_cancelled()` instead of monopolising the
UI thread.

`MayaMcpServer.stop()` calls `dispatcher.shutdown("Interrupted")` on any
dispatcher attached via `server.attach_dispatcher(...)`, so threads blocked
inside `submit_callable` unblock within the normal `event.wait()` poll
instead of hanging when Maya restarts mid-job (issue #89).

## Deployment Guides

- [Multi-instance deployment](docs/guide/multi-instance.md) ([中文](docs/zh/guide/multi-instance.md))
  — run multiple Maya sessions on a single workstation behind one MCP gateway.
  A drop-in `userSetup.py` is provided under
  [`examples/multi-instance/`](examples/multi-instance).

## Development

### Clone and Install

```bash
git clone https://github.com/loonghao/dcc-mcp-maya
cd dcc-mcp-maya
pip install -e ".[dev]"
pytest tests/
```

### Maya Development Setup

#### Unix/macOS

```bash
# Link source code to Maya modules directory
just maya-link

# Install dcc-mcp-core into Maya Python
just maya-install-core maya-py=/path/to/mayapy
# Or if mayapy is on PATH:
just maya-install-core

# Check link status
just maya-status

# Full setup
just maya-dev
```

#### Windows (PowerShell)

```powershell
# Link source code to Maya modules directory
just maya-link-win

# Install dcc-mcp-core into Maya Python
just maya-install-core-win maya-version=2025

# Check link status
just maya-status-win

# Clean up (remove symlinks)
just maya-unlink-win
```

**Note**: Windows symlinks require either:
- Windows Developer Mode enabled (Windows 10/11)
- Or running PowerShell as Administrator

If symlinks fail, the scripts will automatically fall back to copying files (changes will require re-running `just maya-link-win`).

### Verify Installation

```bash
just verify-deps
```

### Run Tests

```bash
just test-quick
```

## License

MIT — see [LICENSE](LICENSE).
