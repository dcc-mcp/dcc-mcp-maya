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

By default the OS assigns a free instance port. Copy the URL printed by the
bootstrap (or run `dcc-mcp-cli list`), for example:

```text
http://127.0.0.1:<assigned-port>/mcp
```

Configure your MCP host with that direct URL:

```json
{
  "mcpServers": {
    "maya-standalone": {
      "url": "http://127.0.0.1:<assigned-port>/mcp"
    }
  }
}
```

Useful environment variables:

| Variable | Default | Use |
|---|---|---|
| `DCC_MCP_MAYA_PORT` | OS-assigned | Optional fixed direct MCP port for this `mayapy` process. |
| `DCC_MCP_GATEWAY_PORT` | `0` in bootstrap | Set `9765` only when you intentionally want gateway registration. |
| `DCC_MCP_MAYA_SKILL_PATHS` | none | Extra skill roots for custom standalone-safe skills. |

There is also a runnable example at
[`examples/standalone/run_maya_mcp.py`](https://github.com/dcc-mcp/dcc-mcp-maya/blob/main/examples/standalone/run_maya_mcp.py):

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
    gateway_port=None,
    host_dispatcher=dispatcher,
)

print(handle.mcp_url())  # exact OS-assigned direct URL
stop = threading.Event()
try:
    while not stop.wait(0.01):
        dispatcher.drain_queue(budget_ms=8)
finally:
    stop_server()
    maya.standalone.uninitialize()
```

`MayaStandaloneDispatcher` queues scene work for Maya's initialization thread.
Call `drain_queue()` on that main thread while HTTP clients run on other
threads or processes. Blocking the owner with `Event.wait()` alone cannot
service scene requests. Readiness remains false until the first pump, and
shutdown interrupts queued calls. `affinity: any` is reserved for pure Python
or filesystem work.

For a long-lived service prefer `serve_headless()` (used by
`mayapy -m dcc_mcp_maya` and the bundled example); it already owns the main-thread
pump, server lifecycle and cleanup through Core's dispatcher.

## Graceful Shutdown on Windows

This section applies to the **Windows standalone** service mode
(`serve_headless()` and `mayapy -m dcc_mcp_maya`). It was verified on Windows
with **Maya 2022, 2024, and 2026**; it is not a statement about other platforms
or about future Maya versions.

The only verified graceful shutdown path for this mode is the programmatic stop
event you pass to `serve_headless(stop_event=...)`. The ownership split
stays the same as at startup: you own Maya initialization and the stop event,
while `serve_headless()` owns its server, its dispatcher, and the
owning-main-thread pump. Setting the event makes the pump loop return, after
which `serve_headless()` runs its `finally` block (`server.stop()` and
`host.stop()`). The process then exits with code 0, the port is released, and
the instance is removed from `services.json` and `locks/`.

Trigger the stop from your own thread or supervisor — for example a watchdog, a
job-completion callback, or an idle timer — not from a console signal (see
below).

```python
import threading

import maya.standalone

from dcc_mcp_maya import serve_headless

maya.standalone.initialize(name="python")

stop_event = threading.Event()
try:
    # Blocks this (main) thread and pumps Core's dispatcher until the event
    # is set. Setting it from another thread ends the loop and runs cleanup:
    #
    #     stop_event.set()
    #
    serve_headless(stop_event=stop_event)
finally:
    maya.standalone.uninitialize()
```

A complete starting point is
[`examples/standalone/run_maya_mcp.py`](https://github.com/dcc-mcp/dcc-mcp-maya/blob/main/examples/standalone/run_maya_mcp.py).

### Console signals are not supported on Windows

In the tested Windows standalone builds, the interactive console shortcuts do
not produce a clean shutdown:

- **Ctrl+C (`CTRL_C_EVENT`)** is ignored — the main thread is blocked inside
  Maya's native dispatcher, so Python's `SIGINT` handler does not run and
  `KeyboardInterrupt` is never raised.
- **Ctrl+Break (`CTRL_BREAK_EVENT`)** terminates the process through Maya's Intel
  Fortran runtime (`forrtl: error (200)`) rather than raising a Python
  `KeyboardInterrupt`, so `try`/`except KeyboardInterrupt` and `finally` cleanup
  in the entrypoint do not run.

Because `python -m dcc_mcp_maya` serves until interrupted, do not rely on a
console signal to stop it on Windows. Drive the lifecycle with the stop event
instead.

### Shutdown methods compared

| Shutdown method | Clean exit | Port released | Registry (`services.json` / `locks/`) |
|---|---|---|---|
| `stop_event.set()` (programmatic) | Yes — rc 0 | Yes | Cleared |
| Ctrl+C (`CTRL_C_EVENT`) | No — ignored; service keeps running | n/a | Unchanged |
| Ctrl+Break (`CTRL_BREAK_EVENT`) | No — killed by the Maya runtime | Yes | Can leave a dead pid record and an orphan `.lock` file |
| Force termination (`taskkill /F`) | No — killed | Yes | Can leave a dead pid record and an orphan `.lock` file |

Force-terminating a standalone service is a known limitation: it can leave a
stale `services.json` row and an orphan lock file behind. The residue is
non-destructive — it does not touch scene data — and is recoverable: Core evicts
dead registry entries automatically the next time it reads the registry, and a
service stopped through the stop-event path leaves no such residue. Prefer the
programmatic stop-event path for any service you need to stop cleanly, and treat
force termination as a last resort rather than a routine workaround; do not make
manual registry or lock-file cleanup part of normal operation.

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
[`examples/standalone/custom-skills/standalone-scene-report`](https://github.com/dcc-mcp/dcc-mcp-maya/tree/main/examples/standalone/custom-skills/standalone-scene-report).

## Existing Examples

- [`maya_bootstrap.py`](https://github.com/dcc-mcp/dcc-mcp-maya/blob/main/maya_bootstrap.py) starts the packaged standalone
  service.
- [`examples/standalone/run_maya_mcp.py`](https://github.com/dcc-mcp/dcc-mcp-maya/blob/main/examples/standalone/run_maya_mcp.py)
  is a copy-paste service script.
- [`examples/standalone/custom-skills/standalone-scene-report`](https://github.com/dcc-mcp/dcc-mcp-maya/tree/main/examples/standalone/custom-skills/standalone-scene-report)
  shows a headless-safe custom skill.
- `tests/e2e_standalone/` contains real `mayapy` E2E coverage for built-in
  tools and MCP protocol calls.

## Common Pitfalls

| Symptom | Fix |
|---|---|
| MCP host cannot connect | Confirm `mayapy` is running, then refresh the direct URL with `dcc-mcp-cli list`. |
| Tool needs viewport or modelPanel | Use GUI plugin mode; headless Maya has no interactive viewport. |
| Custom skill not found | Set `DCC_MCP_MAYA_SKILL_PATHS` to the parent directory of the skill package, then restart the standalone service. |
| Concurrent calls corrupt scene state | Route all Maya-touching tools through `affinity: main`; `MayaStandaloneDispatcher` serializes them. |
