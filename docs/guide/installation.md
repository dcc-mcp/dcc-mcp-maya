# Installation Guide

## Requirements

- **Maya**: 2020+ (tested with Maya 2022 through 2026 module packages)
- **Python**: 3.7 – 3.12 (embedded in Maya)
- **dcc-mcp-core**: ≥ 0.17.23 (auto-installed as dependency)

## Method 1 — pip into mayapy

The simplest approach. Use Maya's own Python interpreter:

```bash
# Generic
mayapy -m pip install "dcc-mcp-maya[sidecar]"

# Windows — Maya 2024
"C:\Program Files\Autodesk\Maya2024\bin\mayapy.exe" -m pip install "dcc-mcp-maya[sidecar]"

# macOS — Maya 2024
/Applications/Autodesk/maya2024/Maya.app/Contents/bin/mayapy -m pip install "dcc-mcp-maya[sidecar]"
```

Verify installation:

```bash
mayapy -c "import dcc_mcp_maya; print(dcc_mcp_maya.__version__)"
```

Use `dcc-mcp-maya` without `[sidecar]` only when your environment already
provides the `dcc-mcp-server` binary.

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
import maya.utils

def _load_dcc_mcp_maya():
    if not cmds.pluginInfo("dcc_mcp_maya_plugin", query=True, loaded=True):
        cmds.loadPlugin("dcc_mcp_maya_plugin", quiet=True)

maya.utils.executeDeferred(_load_dcc_mcp_maya, lowestPriority=True)
```

**File location:**
- Windows: `%USERPROFILE%\Documents\maya\scripts\userSetup.py`
- macOS: `~/Library/Preferences/Autodesk/maya/scripts/userSetup.py`

Avoid calling plain `dcc_mcp_maya.start_server(port=8765)` from Maya GUI
startup code. GUI sessions need a Maya UI dispatcher for `affinity: main` tools;
the plugin installs it for you.

## Method 5 — direct start_server for debugging

Direct server mode is useful for local debugging and `mayapy` scripts. In Maya
GUI, pass a dispatcher explicitly:

```python
from dcc_mcp_maya.dispatcher import MayaUiDispatcher, MayaUiPump
import dcc_mcp_maya

dispatcher = MayaUiDispatcher()
MayaUiPump(dispatcher).install()
handle = dcc_mcp_maya.start_server(port=8765, host_dispatcher=dispatcher)
print(handle.mcp_url())  # http://127.0.0.1:8765/mcp
```

When using direct mode, configure the MCP host with
`http://127.0.0.1:8765/mcp`. In plugin mode, use the gateway URL
`http://127.0.0.1:9765/mcp`.

## Multiple Maya Versions

Each Maya version has its own Python interpreter. Install separately per version:

```bash
# Maya 2022 (Python 3.7)
"C:\Program Files\Autodesk\Maya2022\bin\mayapy.exe" -m pip install "dcc-mcp-maya[sidecar]"

# Maya 2024
"C:\Program Files\Autodesk\Maya2024\bin\mayapy.exe" -m pip install "dcc-mcp-maya[sidecar]"

# Maya 2025
"C:\Program Files\Autodesk\Maya2025\bin\mayapy.exe" -m pip install "dcc-mcp-maya[sidecar]"
```

If running multiple Maya instances simultaneously, plugin gateway mode is
simpler: every instance registers behind `http://127.0.0.1:9765/mcp`.

If you deliberately run direct mode, use different ports:

```python
# Maya 2022 instance
handle = dcc_mcp_maya.start_server(port=8762)

# Maya 2024 instance
handle = dcc_mcp_maya.start_server(port=8764)

# Maya 2025 instance
handle = dcc_mcp_maya.start_server(port=8765)
```

Then configure each as a separate MCP server in your host:

```json
{
  "mcpServers": {
    "maya-2022": { "url": "http://127.0.0.1:8762/mcp" },
    "maya-2024": { "url": "http://127.0.0.1:8764/mcp" },
    "maya-2025": { "url": "http://127.0.0.1:8765/mcp" }
  }
}
```

## Upgrading

```bash
mayapy -m pip install --upgrade dcc-mcp-maya
```

## Uninstalling

```bash
mayapy -m pip uninstall dcc-mcp-maya
```
