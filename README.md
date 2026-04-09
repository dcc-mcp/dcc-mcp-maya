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
   cmds.loadPlugin("dcc_mcp_maya")
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

Copy `maya/plugin/dcc_mcp_maya.py` to a directory on `MAYA_PLUG_IN_PATH`.  
The server starts automatically when the plugin loads.

### Configuration

| Environment variable | Default | Description |
|---|---|---|
| `DCC_MCP_MAYA_PORT` | `8765` | TCP port for the MCP server |
| `DCC_MCP_MAYA_SERVER_NAME` | `maya-mcp` | Name shown in MCP initialize |

## Available MCP Tools

### Scene (7 tools)

| Tool | Description |
|------|-------------|
| `get_session_info` | Maya version, scene path, FPS, object count |
| `new_scene` | Create a new scene |
| `save_scene` | Save scene to disk |
| `open_scene` | Open a scene file |
| `list_objects` | List DAG objects (optional type filter) |
| `get_selection` | Get current selection |
| `set_selection` | Set active selection |

### Geometry (8 tools)

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

### Material (4 tools)

| Tool | Description |
|------|-------------|
| `create_material` | Create Lambert/Blinn/Phong/Arnold material |
| `assign_material` | Assign material to objects |
| `set_material_attribute` | Set material color, roughness, etc. |
| `list_materials` | List all scene materials |

### Animation (5 tools)

| Tool | Description |
|------|-------------|
| `set_keyframe` | Set keyframe on object attributes |
| `get_keyframes` | Get keyframe times for object/attribute |
| `set_timeline` | Set playback timeline range |
| `get_current_time` | Get current frame number |
| `set_current_time` | Set current frame number |

### Render (4 tools)

| Tool | Description |
|------|-------------|
| `set_render_settings` | Set resolution, frame range, renderer |
| `capture_viewport` | Capture viewport as base64-encoded PNG |
| `import_file` | Import FBX/OBJ/Alembic/Maya file |
| `export_selection` | Export selection to FBX/OBJ/Alembic |

### Scripting (2 tools)

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
- [`dcc-mcp-core`](https://github.com/loonghao/dcc-mcp-core) ≥ 0.12.7

## Development

```bash
git clone https://github.com/loonghao/dcc-mcp-maya
cd dcc-mcp-maya
pip install -e ".[dev]"
pytest tests/
```

## License

MIT — see [LICENSE](LICENSE).
