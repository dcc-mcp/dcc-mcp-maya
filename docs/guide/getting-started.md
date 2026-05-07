# Quick Start

Get Maya talking to an MCP host in under 5 minutes.

## Prerequisites

- Maya 2020 or later (Python 3.7+)
- An MCP-compatible host: [Claude Desktop](https://claude.ai/download), [Cursor](https://cursor.sh/), or [OpenClaw](https://github.com/loonghao/openclaw)

## Step 1 — Install

Install into Maya's Python interpreter:

```bash
mayapy -m pip install dcc-mcp-maya
```

For a specific Maya version (Windows example):

```bash
"C:\Program Files\Autodesk\Maya2024\bin\mayapy.exe" -m pip install dcc-mcp-maya
```

## Step 2 — Start the Server

Open Maya's **Script Editor** (Python tab) and run:

```python
import dcc_mcp_maya

handle = dcc_mcp_maya.start_server(port=8765)
print(handle.mcp_url())   # http://127.0.0.1:8765/mcp
```

The server starts immediately in a background thread. Maya remains fully interactive.

## Step 3 — Configure Your MCP Host

### Claude Desktop

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

**File locations:**
- macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
- Windows: `%APPDATA%\Claude\claude_desktop_config.json`

Restart Claude Desktop after editing.

### Cursor

In Cursor settings → MCP Servers, add:

```json
{
  "maya": {
    "url": "http://127.0.0.1:8765/mcp"
  }
}
```

### Any MCP Client

The server exposes a single endpoint:

```
http://127.0.0.1:8765/mcp
```

## Step 4 — Execute Your First Action

In Claude Desktop (or your MCP host), try:

> **"Create a red sphere in Maya"**

Claude will call the `maya_primitives__create_sphere` and `maya_materials__create_material` tools automatically.

Or be more specific:

> **"Create a polygon sphere with radius 2 at position (0, 1, 0) and name it 'ball'"**

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DCC_MCP_MAYA_PORT` | `8765` | TCP port for the MCP server |
| `DCC_MCP_MAYA_SERVER_NAME` | `maya-mcp` | Name shown in MCP `initialize` response |
| `DCC_MCP_MAYA_SKILL_PATHS` | _(empty)_ | Extra skill directories (colon/semicolon separated) |

## Stop the Server

```python
import dcc_mcp_maya
dcc_mcp_maya.stop_server()
```

## Next Steps

- [Installation Guide](./installation) — plugin mode, userSetup.py, multi-Maya setup
- [MCP Tools Guide](./mcp-tools) — full list of available tools with examples
- [Advanced Usage](./advanced) — custom skills, main-thread scheduling
