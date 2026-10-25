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
(`serve_headless()` and `mayapy -m dcc_mcp_maya`). It describes the implemented
cooperative shutdown API and platform constraints, not a version-specific native
acceptance matrix or a guarantee about console-signal behavior in Maya.

`serve_headless(stop_event=...)` is a Python API. The module CLI currently does
not accept or expose a stop event or an external shutdown channel. For a
controllable Windows service, use a custom wrapper that passes its own event
and sets it from an application-owned thread or callback, as outlined below.

Use the programmatic stop event passed to `serve_headless(stop_event=...)`
for cooperative shutdown. The ownership split
stays the same as at startup: you own Maya initialization and the stop event,
while `serve_headless()` owns its server, its dispatcher, and the
owning-main-thread pump. Once any running main-thread operation returns,
setting the event lets the pump loop return and `serve_headless()` runs its
`finally` block (`server.stop()` and `host.stop()`). The function returns to its
caller; it does not terminate the process. After normal wrapper teardown,
verify exit code 0, release of that service's port, and removal of that
instance's `services.json` record and owned lock file. Other instances and
their lock files must remain intact.

Trigger the stop from an application-owned thread or callback — for example a
watchdog, a job-completion callback, or an idle timer — not from a console signal
(see below).

**Skeleton only: no stop trigger is installed below.** Before running this as a
service, wire an application-owned thread or callback to `stop_event.set()`.
Copying this block unchanged leaves the service running; the commented call is
not an implemented shutdown trigger.

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

The existing
[`examples/standalone/run_maya_mcp.py`](https://github.com/dcc-mcp/dcc-mcp-maya/blob/main/examples/standalone/run_maya_mcp.py)
shows the ownership structure, but its stop event is set only by signal
handlers and it prints a Ctrl+C instruction. It is **not a complete Windows
shutdown example**: replace that signal-only trigger with your own
programmatic trigger before relying on it for clean Windows shutdown.

### Do not rely on console signals

Ctrl+C (`CTRL_C_EVENT`) and Ctrl+Break (`CTRL_BREAK_EVENT`) are console control
events, not adapter shutdown commands. Windows applications can alter console
Ctrl+C handling; see [Microsoft's console-signal documentation](https://learn.microsoft.com/en-us/windows/console/ctrl-c-and-ctrl-break-signals).
Python runs its signal handlers on the main interpreter thread, and long native
calls can delay them; see [Python's signal-handler documentation](https://docs.python.org/3/library/signal.html#execution-of-python-signal-handlers).
These platform rules do not establish what a particular Maya release does.
Do not assume either signal will run the adapter's Python cleanup.

Do not rely on a console signal to stop `mayapy -m dcc_mcp_maya` on Windows.
That entrypoint does not inject a stop event; use the custom Python wrapper
above when you need a programmatically controlled lifecycle. This section does
not add a CLI shutdown flag or promise automatic graceful exit.

### Shutdown methods compared

| Shutdown method | Clean exit | Port released | Registry (`services.json` / `locks/`) |
|---|---|---|---|
| `stop_event.set()` (custom wrapper, normal teardown) | Verify rc 0 | Verify released | Verify only this instance's record and owned lock are removed |
| Ctrl+C (`CTRL_C_EVENT`) | Not guaranteed; host-dependent | Check process state | Cleanup not guaranteed |
| Ctrl+Break (`CTRL_BREAK_EVENT`) | Not guaranteed; host-dependent | Check process state | Cleanup not guaranteed |
| Force termination (`taskkill /F`) | No graceful cleanup | After process exit | Can leave a dead pid record and an orphan `.lock` file |

Force-terminating a standalone service is a known limitation: it can leave a
stale `services.json` row and an orphan lock file behind. The residue is
non-destructive by itself — it does not touch scene data — but force-killing
Maya can still lose unsaved work. Core's liveness-aware registry scans and
gateway cleanup can evict dead entries; an arbitrary registry read does not
guarantee cleanup. After a stop-event shutdown, verify this instance's cleanup
as described above rather than deleting unrelated entries or locks. Prefer the
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
