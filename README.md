# dcc-mcp-maya

Maya plugin for the [DCC Model Context Protocol](https://github.com/loonghao/dcc-mcp-core) (MCP) ecosystem.

Embeds a standards-compliant **MCP Streamable HTTP server** (2025-03-26 spec) directly inside Maya — no external gateway or separate IPC process required.

[![CI](https://github.com/loonghao/dcc-mcp-maya/actions/workflows/ci.yml/badge.svg)](https://github.com/loonghao/dcc-mcp-maya/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/loonghao/dcc-mcp-maya/graph/badge.svg)](https://codecov.io/gh/loonghao/dcc-mcp-maya)
[![PyPI](https://img.shields.io/pypi/v/dcc-mcp-maya)](https://pypi.org/project/dcc-mcp-maya/)
[![Python](https://img.shields.io/pypi/pyversions/dcc-mcp-maya)](https://pypi.org/project/dcc-mcp-maya/)
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
│  │  McpHttpServer  (dcc-mcp-core / Rust/axum)      │   │
│  │  POST /mcp  ──►  ToolRegistry                   │   │
│  │  GET  /mcp  ──►  SSE stream                     │   │
│  └─────────────────────────────────────────────────┘   │
└─────────────────────────────┬───────────────────────────┘
                               │  http://127.0.0.1:8765/mcp
┌─────────────────────────────▼───────────────────────────┐
│  MCP Host  (Claude Desktop / OpenClaw / Cursor / …)      │
└─────────────────────────────────────────────────────────┘
```

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
| `DCC_MCP_MAYA_MINIMAL` | `1` | `0` = load all skills at startup (legacy); `1` = minimal core surface |
| `DCC_MCP_MAYA_DEFAULT_TOOLS` | _(none)_ | Comma-separated skill names to load at startup (overrides minimal default) |

### Progressive Loading (Minimal Mode)

By default, `dcc-mcp-maya` boots with a **minimal tool surface** — only core
skills (`maya-scripting`, `maya-scene`) are loaded, and within those only the
essential tools are active:

| Tool | Role | Source skill |
|------|------|-------------|
| `execute_python` | Write + execute | `maya-scripting` (core group) |
| `execute_mel` | Write + execute | `maya-scripting` (core group) |
| `get_scene_info` | Read | `maya-scene` (core group) |
| `get_selection` | Read | `maya-scene` (core group) |
| `get_session_info` | Read | `maya-scene` (core group) |
| `search_tools` | Discover | core |
| `list_skills` | Browse | core |
| `load_skill` | Progressive activation | core |

All other skills appear as `__skill__<name>` stubs. The agent calls
`load_skill("maya-primitives")` to expand the surface on demand, and
`activate_group("extended")` to expose additional tool groups within a
loaded skill.

**Opt out** (restore legacy full-load):

```bash
# Environment variable
export DCC_MCP_MAYA_MINIMAL=0
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
export DCC_MCP_MAYA_DEFAULT_TOOLS="maya-scripting,maya-scene,maya-primitives"
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

## Available MCP Tools

`dcc-mcp-maya` ships **12 built-in skill packages** and **73+ Maya MCP tools**.
In the default minimal mode, only the core tools above are active at startup;
the rest are progressively loaded via `load_skill`.

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
| `capture_viewport` | Capture viewport as base64-encoded PNG |
| `import_file` | Import FBX/OBJ/Alembic/Maya file |
| `export_selection` | Export selection to FBX/OBJ/Alembic |

### Skill Routing Decision Tree

When an agent receives a request that requires a Maya operation, follow this
routing logic:

```
Intent matches a domain skill (shot export, render farm, scene assembly)?
  → load that skill.
Intent matches a primitive (create cube, move object, set attr)?
  → load maya-scripting, read RECIPES.md (if available), call execute_python.
Error on a wrapped tool?
  → read _meta.dcc.raw_trace, switch to execute_python with the corrected call.
```

`maya-scripting` is the **explicit fall-through entry point** — when no
dedicated domain skill covers the request, the agent should use
`execute_python` / `execute_mel` to write the call directly rather than
guess or invent API usage from memory.

### Scripting

| Tool | Description |
|------|-------------|
| `execute_mel` | Execute a MEL script |
| `execute_python` | Execute Python inside Maya |

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
- [`dcc-mcp-core`](https://github.com/loonghao/dcc-mcp-core) ≥ 0.12.29

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

## Authoring Skills: Execution & Affinity

Every tool declared in a `tools.yaml` file must tell the MCP gateway **how** it
should be dispatched.  This is what lets the gateway return an async `job_id`
instead of blocking, and what prevents main-thread-affine tools from running
on a worker thread and crashing Maya.

Each entry in `tools.yaml` supports three dispatch fields:

```yaml
tools:
  - name: render_frames
    execution: async          # long-running — spawn as a Job
    affinity: main            # cmds.render touches scene state
    timeout_hint_secs: 600    # required when execution: async
  - name: get_scene_info
    execution: sync
    affinity: main            # cmds.ls is main-thread-only
  - name: list_render_presets
    execution: sync
    affinity: any             # pure filesystem read — worker-thread safe
```

Rules of thumb:

| Property | Guidance |
|---|---|
| `execution: async` | Use for anything that typically runs > 2s (render, bake, simulation, large I/O). Must declare `timeout_hint_secs`. |
| `execution: sync` | Use for fast queries, attribute edits, and small creations. |
| `affinity: main` | **Default**. Anything that calls `maya.cmds` or `OpenMaya`. |
| `affinity: any`  | Pure Python / filesystem only — never touches Maya state. |

Two helpers keep the annotations consistent across the 12 bundled skills:

```bash
# Annotate every bundled tools.yaml from the SKILL_DEFAULTS table.
python tools/annotate_skill_affinity.py

# CI enforcement — fails if any tool is missing affinity/execution
# or if an async tool is missing timeout_hint_secs.
python tools/lint_skill_affinity.py
```

Third-party skill authors should run `tools/lint_skill_affinity.py` against
their own skill packages before publishing.  See issue
[#84](https://github.com/loonghao/dcc-mcp-maya/issues/84) for the full
categorisation matrix.

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
