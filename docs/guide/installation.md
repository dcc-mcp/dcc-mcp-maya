# Installation Guide

## Requirements

- **Maya**: 2020+ (tested with Maya 2022 through 2026 module packages)
- **Python**: 3.7 – 3.12 (embedded in Maya)
- **dcc-mcp-core**: ≥ 0.19.45 (auto-installed as dependency)
- **dcc-mcp-server**: ≥ 0.18.21 (auto-installed as dependency for the default sidecar gateway)

## Method 1 — pip into mayapy

The simplest approach. Use Maya's own Python interpreter:

```bash
# Generic
mayapy -m pip install dcc-mcp-maya

# Windows — Maya 2024
"C:\Program Files\Autodesk\Maya2024\bin\mayapy.exe" -m pip install dcc-mcp-maya

# macOS — Maya 2024
/Applications/Autodesk/maya2024/Maya.app/Contents/bin/mayapy -m pip install dcc-mcp-maya
```

Verify installation:

```bash
mayapy -c "import dcc_mcp_maya; print(dcc_mcp_maya.__version__)"
```

Release module ZIPs follow the same rule: they include the Maya plugin,
`dcc-mcp-maya`, the in-process bridge dependencies such as `dcc-mcp-core`, and
the `dcc-mcp-server` sidecar binary used by the default gateway path. Verify
clean module deployments with `mayapy -c "from dcc_mcp_maya.sidecar import resolve_sidecar_binary; print(resolve_sidecar_binary())"`.

## Method 2 — Maya Plugin

This is the recommended GUI path. Copy the plugin file to a directory on
`MAYA_PLUG_IN_PATH`, then load it through the Plug-in Manager.

1. Copy `maya/plugin/dcc_mcp_maya_plugin.py` to your Maya plugins folder, e.g.:
   - Windows: `%USERPROFILE%\Documents\maya\2024\plug-ins\`
   - macOS: `~/Library/Preferences/Autodesk/maya/2024/plug-ins/`

2. Open **Window → Settings/Preferences → Plug-in Manager**

3. Find `dcc_mcp_maya` and check **Loaded** (and optionally **Auto load**)

The plugin starts the server automatically on load. By default it uses an OS-assigned instance port and participates in the gateway on port `9765`.

In default sidecar mode, local MCP clients use `http://127.0.0.1:9765/mcp`. Newer sidecar binaries ensure a standalone gateway and can expose it on the LAN at `http://<this-machine-lan-ip>:59765/mcp`. Set `DCC_MCP_GATEWAY_REMOTE_PORT=0` to disable the LAN listener, or override `DCC_MCP_GATEWAY_NAME`, `DCC_MCP_GATEWAY_REMOTE_HOST`, and `DCC_MCP_GATEWAY_REMOTE_PORT` before loading the plugin.

During plugin initialization, `dcc-mcp-maya` also closes Maya's legacy MEL commandPort on `127.0.0.1:50007`. The MCP server never uses that port, and closing it prevents accidental HTTP probes from opening Maya's security warning dialog. Studios that still depend on the legacy commandPort can opt out with `DCC_MCP_MAYA_CLOSE_DEFAULT_COMMANDPORT=0` before loading the plugin.

The plugin starts the Rust sidecar beside Maya by default while keeping the
embedded in-process MCP server as the host bridge. Set `DCC_MCP_MAYA_SIDECAR=0`
before loading the plugin to return to the legacy in-process gateway path.
Sidecar mode uses the in-Maya Qt event-loop dispatcher and does not require
opening Maya's legacy commandPort.

Configure MCP clients with:

```json
{
  "mcpServers": {
    "maya": {
      "url": "http://127.0.0.1:9765/mcp"
    }
  }
}
```

## Non-interactive GUI bootstrap diagnosis

For unattended Maya 2025 GUI startup, use the adapter's fixed launcher instead
of composing MEL, Python, or `-script` payloads. Run it with the same `mayapy`
where `dcc-mcp-maya` is installed:

```bash
# Windows
"C:\Program Files\Autodesk\Maya2025\bin\mayapy.exe" -m dcc_mcp_maya.gui_bootstrap launch --maya-executable "C:\Program Files\Autodesk\Maya2025\bin\maya.exe" --timeout 120

# macOS
/Applications/Autodesk/maya2025/Maya.app/Contents/bin/mayapy -m dcc_mcp_maya.gui_bootstrap launch --maya-executable /Applications/Autodesk/maya2025/Maya.app/Contents/MacOS/Maya --timeout 120

# Linux
/usr/autodesk/maya2025/bin/mayapy -m dcc_mcp_maya.gui_bootstrap launch --maya-executable /usr/autodesk/maya2025/bin/maya --timeout 120
```

The example uses Maya 2025; replace the versioned executable paths with any
supported Maya installation. The command and diagnostic contract are
version-independent.

The command launches Maya once, leaves the GUI running, and prints one JSON
diagnosis. Exit `0` means that the launched Maya PID has a matching registry
row; exit `10` means that the bounded probe diagnosed a startup stage; exit
`40` means the launch arguments or executable were invalid. The four bounded
failure reasons are `plugin_not_invoked`, `plugin_load_failed`,
`sidecar_failed`, and `registry_registration_failed`. `next_action` is the
machine-readable recovery step.

The JSONL path is returned as `bootstrap_log`. Its ordered stages cover plug-in
invocation/resolution/load, adapter import, registry registration, sidecar
spawn, and completion before readiness is declared. To inspect the same launch
again without starting another Maya process, use:

```bash
mayapy -m dcc_mcp_maya.gui_bootstrap probe --maya-pid <PID> --log-path <BOOTSTRAP_LOG> --timeout 30
```

Pass `--registry-dir` only when Maya uses the matching
`DCC_MCP_REGISTRY_DIR` base. This path does not change Plug-in Manager's
**Loaded** or **Auto load** settings, and it never evaluates caller-supplied
MEL/Python or falls back to UI automation. A live Maya installation and license
are still required for the GUI proof.

## Method 3 — mayapy bootstrap

For headless E2E or service-style runs, start Maya through the bundled bootstrap:

```bash
mayapy maya_bootstrap.py
```

The bootstrap creates a Maya host dispatcher in batch mode, exposes MCP at `/mcp`, and exposes the per-DCC REST skill API at `/v1/*` through the core host bridge.

Maya licensing is required for CI. Gate this command behind a self-hosted runner or a licensed Maya environment.

See [Standalone mayapy Services](./standalone.md) for MCP host configuration,
custom bootstrap code, and standalone-safe custom skill examples.

## Method 4 — userSetup.py (Auto-start)

To start MCP every time Maya opens, prefer copying or sourcing the bundled
`maya/userSetup.py`. It sets safe plugin defaults, finds module installs, and
defers plugin loading until Maya is idle.

Minimal custom `userSetup.py`:

```python
# userSetup.py
import maya.cmds as cmds

def _load_dcc_mcp_maya():
    if not cmds.pluginInfo("dcc_mcp_maya_plugin", query=True, loaded=True):
        cmds.loadPlugin("dcc_mcp_maya_plugin", quiet=True)

cmds.evalDeferred(_load_dcc_mcp_maya, lowestPriority=True)
```

**File location:**
- Windows: `%USERPROFILE%\Documents\maya\scripts\userSetup.py`
- macOS: `~/Library/Preferences/Autodesk/maya/scripts/userSetup.py`

Avoid calling plain `dcc_mcp_maya.start_server()` from Maya GUI startup code.
GUI sessions need a Maya UI dispatcher for `affinity: main` tools; the plugin
installs it for you.

## Method 5 — direct start_server for debugging

Direct server mode is useful for local debugging and `mayapy` scripts. In Maya
GUI, pass a dispatcher explicitly:

```python
from dcc_mcp_maya.dispatcher import MayaUiDispatcher, MayaUiPump
import dcc_mcp_maya

dispatcher = MayaUiDispatcher()
MayaUiPump(dispatcher).install()
handle = dcc_mcp_maya.start_server(host_dispatcher=dispatcher)
print(handle.mcp_url())  # exact OS-assigned direct URL
```

When using direct mode, configure the MCP host with the URL returned by
`handle.mcp_url()`. In plugin mode, use the stable gateway URL
`http://127.0.0.1:9765/mcp`; `dcc-mcp-cli list` reports every registered
instance and its exact bound URL.

## Multiple Maya Versions

Each Maya version has its own Python interpreter. Install separately per version:

```bash
# Maya 2022 (Python 3.7)
"C:\Program Files\Autodesk\Maya2022\bin\mayapy.exe" -m pip install dcc-mcp-maya

# Maya 2024
"C:\Program Files\Autodesk\Maya2024\bin\mayapy.exe" -m pip install dcc-mcp-maya

# Maya 2025
"C:\Program Files\Autodesk\Maya2025\bin\mayapy.exe" -m pip install dcc-mcp-maya
```

If running multiple Maya instances simultaneously, plugin gateway mode is
simpler: every instance registers behind `http://127.0.0.1:9765/mcp`.

Direct servers also bind independent OS-assigned ports, so no manual port range
or pre-bind probe is needed:

```python
# Run this independently inside each Maya process.
handle = dcc_mcp_maya.start_server()
print(handle.mcp_url())
```

In normal multi-process use, let every process register with the gateway and
select the target instance through discovery metadata rather than copying
these transient direct URLs into a persistent client configuration.

## Upgrading

```bash
mayapy -m pip install --upgrade dcc-mcp-maya
```

## Uninstalling

```bash
mayapy -m pip uninstall dcc-mcp-maya
```
