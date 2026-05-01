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

## Long-Running Scripts: `defer=True`

`execute_python` and any custom skill that returns a `DeferredToolResult` can keep the MCP request thread responsive while a long-running script (bake, render, simulation, IO) runs on Maya's idle queue.

### When to use it

| Scenario | Recommendation |
|---|---|
| Quick query / attribute write (< 1s) | `defer=False` (default) — synchronous reply |
| Wall-clock 1–60s, no UI needed | `defer=True` — client polls until done |
| Multi-minute work (renders, caches) | `defer=True` + raise `timeout_secs` |
| Anything that must block the request | `defer=False` (default) |

### From an MCP client (Claude / Cursor / Gemini)

```jsonc
// tools/call request
{
  "jsonrpc": "2.0", "id": 7, "method": "tools/call",
  "params": {
    "name": "maya_scripting__execute_python",
    "arguments": {
      "code": "import maya.cmds as cmds\nfor f in range(1, 240):\n    cmds.currentTime(f)\n    cmds.refresh()\n",
      "defer": true,
      "timeout_secs": 600
    }
  }
}
```

The server returns immediately with a deferred handle; `dcc-mcp-core` polls the handle every 100&nbsp;ms and streams the final `ToolResult` back to the client when the script completes (or `timeout_secs` elapses).

### Cancellation

Long-running scripts that opt into `defer=True` should also cooperate with cancellation:

```python
from dcc_mcp_maya import check_maya_cancelled

for frame in frames:
    check_maya_cancelled()       # raises CancelledError when cancelled
    cmds.currentTime(frame)
    cmds.render()
```

When the MCP client sends `notifications/cancelled` (or the dispatcher signals cancellation), `check_maya_cancelled()` raises and the deferred handle resolves with a structured error envelope.

### Returning `DeferredToolResult` from a custom skill

Any skill can adopt the same pattern by importing the helper from `dcc-mcp-core`:

```python
"""my_long_action.py"""
from typing import Any, Dict


def _runner(state: Dict[str, Any], target: str) -> None:
    import maya.cmds as cmds
    cmds.bakeResults(target, simulation=True, time=(1, 240))
    state["result"] = {"success": True, "message": "Bake complete"}
    state["done"] = True


def main(target: str, defer: bool = True, timeout_secs: float = 600.0):
    if not defer:
        # Synchronous fallback (blocks the request thread).
        state: Dict[str, Any] = {"done": False, "result": None}
        _runner(state, target)
        return state["result"]

    from dcc_mcp_core._server import DeferredToolResult  # lazy import

    state = {"done": False, "result": None}

    def _kick() -> None:
        _runner(state, target)

    try:
        import maya.utils
        maya.utils.executeDeferred(_kick)
    except ImportError:
        # mayapy / standalone — no idle queue; run inline.
        _kick()

    return DeferredToolResult(
        check_is_finished=lambda: state["result"] if state["done"] else None,
        timeout_secs=float(timeout_secs),
        poll_interval_secs=0.1,
    )
```

Declare it as `execution: async` in `tools.yaml` so the dispatcher allocates a worker slot:

```yaml
- name: my_long_action
  execution: async
  affinity: main
  timeout_hint_secs: 600
  inputSchema:
    type: object
    properties:
      target: { type: string }
      defer: { type: boolean, default: true }
      timeout_secs: { type: integer, default: 600, minimum: 1 }
```

### How the dispatcher routes deferred results

`MayaMcpServer._executor` duck-types the return value: if it exposes `check_is_finished`, the result is passed straight through to `dcc-mcp-core`'s poll loop. No wrapping, no copy, no main-thread reflection. This means dispatcher errors raised before the deferred kick-off are still caught and returned as structured `{"success": False, ...}` envelopes, while the polled completion uses your skill's own envelope.

### Configuration knobs

| Env / arg | Default | Effect |
|---|---|---|
| `defer=True` (per-call argument) | `false` | Opt the call into the deferred path. |
| `timeout_secs` (per-call argument) | `3600` | Hard timeout enforced by the core poll loop. |
| `poll_interval_secs` (constructor) | `0.1` | How often the core re-checks `check_is_finished`. |
| Tool's `timeout_hint_secs` (`tools.yaml`) | — | Advisory hint surfaced to the MCP host UI. |

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
