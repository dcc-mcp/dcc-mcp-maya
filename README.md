# dcc-mcp-maya

Maya plugin for the [DCC Model Context Protocol](https://github.com/loonghao/dcc-mcp-core) (MCP) ecosystem.

Embeds a standards-compliant **MCP Streamable HTTP server** (2025-03-26 spec) directly inside Maya — no external gateway or separate IPC process required.

[![CI](https://github.com/loonghao/dcc-mcp-maya/actions/workflows/ci.yml/badge.svg)](https://github.com/loonghao/dcc-mcp-maya/actions/workflows/ci.yml)
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
│  │  POST /mcp  ──►  ActionRegistry                 │   │
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
| `get_action_metrics` | `ActionRecorder` performance counters |
| `dispatch_action` | Relay for `workflow__run_chain` |

The `DCC_MCP_IPC_ADDRESS` environment variable is set automatically so skill
subprocesses can connect back without any manual configuration.

## Available MCP Tools

`dcc-mcp-maya` currently ships **64 built-in skill packages** and **370+ Maya MCP tools**.
The sections below are representative categories, not an exhaustive inventory.
Skill discovery is **progressive**: `register_builtin_actions()` indexes available skills,
and individual skill toolsets are loaded on demand by the MCP server.

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

## Development

```bash
git clone https://github.com/loonghao/dcc-mcp-maya
cd dcc-mcp-maya
pip install -e ".[dev]"
pytest tests/
```

## License

MIT — see [LICENSE](LICENSE).
