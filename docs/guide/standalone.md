# Standalone mayapy Services

Use standalone mode when Maya should run as a headless service: CI, render farm
helpers, batch asset processing, or a long-lived `mayapy` process controlled by
an MCP host.

GUI plugin mode remains the normal artist-workstation path. Standalone mode is
different: no Qt UI event loop, no model panels, no plugin sidecar banner. You
start a `mayapy` process, initialize `maya.standalone`, and expose MCP directly.

## Start a Standalone MCP Server

The bundled bootstrap is the shortest path:

```bash
mayapy maya_bootstrap.py
```

By default it listens on:

```text
http://127.0.0.1:8765/mcp
```

Configure your MCP host with that direct URL:

```json
{
  "mcpServers": {
    "maya-standalone": {
      "url": "http://127.0.0.1:8765/mcp"
    }
  }
}
```

Useful environment variables:

| Variable | Default | Use |
|---|---|---|
| `DCC_MCP_MAYA_PORT` | `8765` | Direct MCP port for this `mayapy` process. |
| `DCC_MCP_GATEWAY_PORT` | `0` in bootstrap | Set `9765` only when you intentionally want gateway registration. |
| `DCC_MCP_MAYA_SKILL_PATHS` | none | Extra skill roots for custom standalone-safe skills. |

There is also a runnable example at
[`examples/standalone/run_maya_mcp.py`](https://github.com/loonghao/dcc-mcp-maya/blob/main/examples/standalone/run_maya_mcp.py):

```bash
mayapy examples/standalone/run_maya_mcp.py
```

## Custom Bootstrap

If you need full control, initialize Maya and attach the standalone dispatcher:

```python
import threading
import maya.standalone

from dcc_mcp_maya import start_server, stop_server
from dcc_mcp_maya.dispatcher import MayaStandaloneDispatcher

maya.standalone.initialize(name="python")

dispatcher = MayaStandaloneDispatcher()
handle = start_server(
    port=8765,
    gateway_port=None,
    host_dispatcher=dispatcher,
)

print(handle.mcp_url())  # http://127.0.0.1:8765/mcp
threading.Event().wait()
```

`MayaStandaloneDispatcher` runs Maya work serially under one process-wide lock.
It advertises support for both `main` and `any` affinity, but there is no UI
thread to marshal onto. The important guarantee is that concurrent HTTP calls
do not enter `maya.cmds` at the same time.

## Writing Standalone-Safe Skills

Most typed Maya skills work unchanged in `mayapy` when they follow the normal
rules:

- Lazy-import `maya.cmds` inside the tool function.
- Declare `affinity: main` for any tool that touches Maya scene state.
- Avoid UI-only commands such as model panels, viewport capture, file dialogs,
  prompt dialogs, and interactive selection workflows.
- Poll `check_maya_cancelled()` in long loops.
- Use `affinity: any` only for pure Python or filesystem work that never imports
  `maya.*`.

Minimal skill script:

```python
from dcc_mcp_core.skill import skill_entry
from dcc_mcp_maya.api import maya_success, maya_from_exception


def create_batch_cube(name: str = "batch_cube") -> dict:
    try:
        import maya.cmds as cmds

        result = cmds.polyCube(name=name)
        return maya_success("Created cube", object_name=result[0])
    except Exception as exc:
        return maya_from_exception(exc, message="Failed to create cube")


@skill_entry
def main(**kwargs) -> dict:
    return create_batch_cube(**kwargs)
```

Matching `tools.yaml`:

```yaml
tools:
  - name: create_batch_cube
    description: Create a cube in mayapy / Maya standalone.
    execution: sync
    affinity: main
    inputSchema:
      type: object
      properties:
        name:
          type: string
          default: batch_cube
```

Load custom skills by pointing `DCC_MCP_MAYA_SKILL_PATHS` at the directory that
contains skill packages:

```bash
# Windows PowerShell
$env:DCC_MCP_MAYA_SKILL_PATHS = "$PWD\examples\standalone\custom-skills"
mayapy examples/standalone/run_maya_mcp.py
```

The repo includes a complete example skill at
[`examples/standalone/custom-skills/standalone-scene-report`](https://github.com/loonghao/dcc-mcp-maya/tree/main/examples/standalone/custom-skills/standalone-scene-report).

## Existing Examples

- [`maya_bootstrap.py`](https://github.com/loonghao/dcc-mcp-maya/blob/main/maya_bootstrap.py) starts the packaged standalone
  service.
- [`examples/standalone/run_maya_mcp.py`](https://github.com/loonghao/dcc-mcp-maya/blob/main/examples/standalone/run_maya_mcp.py)
  is a copy-paste service script.
- [`examples/standalone/custom-skills/standalone-scene-report`](https://github.com/loonghao/dcc-mcp-maya/tree/main/examples/standalone/custom-skills/standalone-scene-report)
  shows a headless-safe custom skill.
- `tests/e2e_standalone/` contains real `mayapy` E2E coverage for built-in
  tools and MCP protocol calls.

## Common Pitfalls

| Symptom | Fix |
|---|---|
| MCP host cannot connect | Confirm the `mayapy` process is still running and the host points at `http://127.0.0.1:8765/mcp`. |
| Tool needs viewport or modelPanel | Use GUI plugin mode; headless Maya has no interactive viewport. |
| Custom skill not found | Set `DCC_MCP_MAYA_SKILL_PATHS` to the parent directory of the skill package, then restart the standalone service. |
| Concurrent calls corrupt scene state | Route all Maya-touching tools through `affinity: main`; `MayaStandaloneDispatcher` serializes them. |
