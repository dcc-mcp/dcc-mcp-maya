# Advanced Usage

## Custom Skills

Create your own skill packages and expose them as MCP tools.

### Skill Directory Structure

```
my-custom-skill/
├── SKILL.md           ← required manifest
└── scripts/
    ├── my_action.py   ← becomes tool: my_custom_skill__my_action
    └── another.py
```

### SKILL.md Format

```yaml
---
name: my-custom-skill
description: "My custom Maya automation skill"
dcc: maya
version: "1.0.0"
tags: [maya, custom]
license: "MIT"
allowed-tools: ["Bash", "Read"]
depends: []
---

# my-custom-skill

Describe what this skill does.

## Scripts

- `my_action` — Description of this action
```

### Action Script Structure

```python
"""Module docstring — becomes the MCP tool description."""

# Import built-in modules
from typing import Any, Dict

# Import third-party modules
import maya.cmds as cmds


def main(
    object_name: str,
    value: float = 1.0,
) -> Dict[str, Any]:
    """Action docstring — shown in MCP tools/list.

    Args:
        object_name: The Maya object to operate on.
        value: A numeric parameter with a default.

    Returns:
        dict with 'success' key and optional result data.
    """
    # ... implementation ...
    result = cmds.getAttr(f"{object_name}.translateY")
    return {
        "success": True,
        "object": object_name,
        "value": result,
    }
```

### Register Your Skills

```python
import dcc_mcp_maya

handle = dcc_mcp_maya.start_server(
    port=8765,
    extra_skill_paths=[
        "/path/to/my-skills-folder",
        "/another/skills/directory",
    ]
)
```

Or use the environment variable:

```bash
# Semicolon-separated on Windows
set DCC_MCP_MAYA_SKILL_PATHS=C:\studio\maya-skills;C:\personal\skills

# Colon-separated on Linux/macOS
export DCC_MCP_MAYA_SKILL_PATHS=/studio/maya-skills:/personal/skills
```

## Main-Thread Scheduling

Maya's UI and `cmds` operations must run on the **main thread**. The plugin entry points and startup helpers are written with that constraint in mind, and any custom code that touches Maya UI state should still be scheduled carefully.

If you write custom code that needs main-thread execution:

```python
import maya.utils

def _my_operation():
    import maya.cmds as cmds
    cmds.polySphere()

# Schedule for next idle on main thread
maya.utils.executeDeferred(_my_operation)

# Or wait for result (use with caution — can deadlock if called from main thread)
result = maya.utils.executeInMainThreadWithResult(_my_operation)
```

## Server Configuration

### Custom Port and Name

```python
import dcc_mcp_maya

handle = dcc_mcp_maya.start_server(
    port=9000,
    server_name="maya-studio-2024",
)
print(handle.mcp_url())   # http://127.0.0.1:9000/mcp
```

### Using MayaMcpServer Directly

For more control, use the class directly:

```python
from dcc_mcp_maya.server import MayaMcpServer

server = MayaMcpServer(
    port=8765,
    server_name="maya-mcp",
)
server.register_builtin_actions(
    extra_skill_paths=["/my/custom/skills"]
)
handle = server.start()

# Later:
server.stop()
```

### Check Server Status

```python
from dcc_mcp_maya.server import _server_instance

if _server_instance and _server_instance.is_running:
    print(f"Running at: {_server_instance.mcp_url}")
```

## Inspect Available Tools

Once the server is running, query the MCP endpoint:

```bash
# List all available tools
curl http://127.0.0.1:8765/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}'
```

## Hot-Reload Skills

Skills can be reloaded without restarting the server (requires dcc-mcp-core v0.13+):

```python
from dcc_mcp_maya.server import _server_instance

# Reload a specific skill
_server_instance._server.load_skill("my-custom-skill")
```

## Logging

Enable debug logging for troubleshooting:

```python
import logging
logging.getLogger("dcc_mcp_maya").setLevel(logging.DEBUG)
logging.getLogger("dcc_mcp_core").setLevel(logging.DEBUG)
```

Or set the environment variable:

```bash
set DCC_MCP_LOG_LEVEL=DEBUG
```

## Production Considerations

### Security

The MCP server listens on `127.0.0.1` (localhost) by default — it is **not accessible from other machines**. If you need network access, use a reverse proxy with authentication.

### Resource Management

The server runs in a background thread and consumes minimal resources when idle. For long-running Maya sessions, monitor the server health via:

```python
import dcc_mcp_maya
# If handle is alive, server is running
handle = dcc_mcp_maya.start_server()
print(handle.port)
```

### Studio Integration

For studio deployments, use `userSetup.py` with conditional startup:

```python
# userSetup.py
import os
import maya.utils

def _start_mcp_if_enabled():
    if os.environ.get("DCC_MCP_MAYA_AUTOSTART", "1") == "0":
        return
    import dcc_mcp_maya
    port = int(os.environ.get("DCC_MCP_MAYA_PORT", "8765"))
    handle = dcc_mcp_maya.start_server(port=port)
    print(f"[studio] Maya MCP: {handle.mcp_url()}")

maya.utils.executeDeferred(_start_mcp_if_enabled)
```
