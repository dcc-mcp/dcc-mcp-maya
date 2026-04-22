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

`dcc-mcp-maya` ships **64 built-in skill packages** and **370+ Maya MCP tools**.
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

### Scripting

| Tool | Description |
|------|-------------|
| `execute_mel` | Execute a MEL script |
| `execute_python` | Execute Python inside Maya |

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

Two helpers keep the annotations consistent across the 64 bundled skills:

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
