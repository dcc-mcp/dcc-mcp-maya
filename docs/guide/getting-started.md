# Getting Started

Get `dcc-mcp-maya` running and connected to an AI host in under 5 minutes.

## Prerequisites

- Maya 2020 or later (Python 3.7+)
- An MCP-compatible AI host: [Claude Desktop](https://claude.ai/download), [Cursor](https://cursor.com), or [OpenClaw](https://github.com/loonghao/openclaw)

## Step 1 — Install the Package

Open a terminal and install into Maya's Python:

```bash
# Using mayapy directly
mayapy -m pip install dcc-mcp-maya

# Or using the full path (Windows example)
"C:\Program Files\Autodesk\Maya2026\bin\mayapy.exe" -m pip install dcc-mcp-maya
```

::: tip Maya 2020–2022
These ship with Python 3.7. The package is compatible, but you may need to upgrade `pip` first:
```bash
mayapy -m pip install --upgrade pip
```
:::

## Step 2 — Start the MCP Server

Inside Maya's **Script Editor** (Python tab), run:

```python
import dcc_mcp_maya

handle = dcc_mcp_maya.start_server(port=8765)
print(handle.mcp_url())  # http://127.0.0.1:8765/mcp
```

You should see output like:
```
http://127.0.0.1:8765/mcp
```

The server is now running. Maya continues to work normally — the server runs on a background thread.

### Auto-start via userSetup.py

To start the server every time Maya launches, add to your `userSetup.py`:

```python
import maya.utils

def _start_mcp():
    import dcc_mcp_maya
    dcc_mcp_maya.start_server(port=8765)

maya.utils.executeDeferred(_start_mcp)
```

## Step 3 — Configure Your AI Host

### Claude Desktop

Edit `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS) or
`%APPDATA%\Claude\claude_desktop_config.json` (Windows):

```json
{
  "mcpServers": {
    "maya": {
      "url": "http://127.0.0.1:8765/mcp"
    }
  }
}
```

Restart Claude Desktop. You should see **maya** listed as a connected MCP server.

### Cursor

In Cursor settings → MCP → Add server:

```json
{
  "maya": {
    "url": "http://127.0.0.1:8765/mcp"
  }
}
```

### Any MCP-Compatible Host

Point it at:
```
http://127.0.0.1:8765/mcp
```

## Step 4 — Run Your First Action

In Claude Desktop, type:

> Create a red polygon sphere named "hero_ball" at position (0, 5, 0)

Claude will call:
1. `maya_primitives__create_sphere` to create the sphere
2. `maya_materials__create_material` to create a red Lambert material
3. `maya_materials__assign_material` to assign it
4. `maya_scene__set_transform` (or `maya_primitives__set_transform`) to position it

You'll see the sphere appear in your Maya viewport in real time.

## Step 5 — Stop the Server

```python
import dcc_mcp_maya
dcc_mcp_maya.stop_server()
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DCC_MCP_MAYA_PORT` | `8765` | TCP port |
| `DCC_MCP_MAYA_SERVER_NAME` | `maya-mcp` | Name shown in MCP `initialize` |
| `DCC_MCP_MAYA_SKILL_PATHS` | — | Extra skill directories (`;`-separated) |
| `DCC_MCP_SKILL_PATHS` | — | Global fallback skill paths |

## Troubleshooting

**Port already in use:**
```python
handle = dcc_mcp_maya.start_server(port=0)  # random available port
print(handle.mcp_url())
```

**Server not found by host:**
Check Maya's Script Editor output for startup errors. The server logs at `INFO` level:
```
Maya MCP server started at http://127.0.0.1:8765/mcp
```

**Actions not loading:**
```python
import logging
logging.basicConfig(level=logging.DEBUG)
import dcc_mcp_maya
dcc_mcp_maya.start_server()
```

## Next Steps

- [Available Actions](/guide/actions) — Full list of built-in MCP tools
- [MCP Tools Guide](/guide/mcp-tools) — How to use tools from the AI side
- [Advanced Usage](/guide/advanced) — Custom skills, plugin mode, hot-reload
