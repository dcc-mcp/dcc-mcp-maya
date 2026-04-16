# Installation Guide

## Requirements

- **Maya**: 2020, 2022, 2023, 2024, or 2025
- **Python**: 3.7 – 3.12 (embedded in Maya)
- **dcc-mcp-core**: ≥ 0.12.29 (auto-installed as dependency)

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

## Method 2 — Maya Plugin

Copy the plugin file to a directory on `MAYA_PLUG_IN_PATH`, then load it through the Plug-in Manager.

1. Copy `maya/plugin/dcc_mcp_maya_plugin.py` to your Maya plugins folder, e.g.:
   - Windows: `%USERPROFILE%\Documents\maya\2024\plug-ins\`
   - macOS: `~/Library/Preferences/Autodesk/maya/2024/plug-ins/`

2. Open **Window → Settings/Preferences → Plug-in Manager**

3. Find `dcc_mcp_maya` and check **Loaded** (and optionally **Auto load**)

The plugin starts the server automatically on load. By default it uses an OS-assigned instance port and participates in the gateway on port `9765`.

## Method 3 — userSetup.py (Auto-start)

To start the server automatically every time Maya opens, add to `userSetup.py`:

```python
# userSetup.py
import maya.utils

def _start_mcp():
    import dcc_mcp_maya
    handle = dcc_mcp_maya.start_server(port=8765)
    print(f"[dcc-mcp-maya] Server started: {handle.mcp_url()}")

maya.utils.executeDeferred(_start_mcp)
```

**File location:**
- Windows: `%USERPROFILE%\Documents\maya\scripts\userSetup.py`
- macOS: `~/Library/Preferences/Autodesk/maya/scripts/userSetup.py`

## Multiple Maya Versions

Each Maya version has its own Python interpreter. Install separately per version:

```bash
# Maya 2022
"C:\Program Files\Autodesk\Maya2022\bin\mayapy.exe" -m pip install dcc-mcp-maya

# Maya 2024
"C:\Program Files\Autodesk\Maya2024\bin\mayapy.exe" -m pip install dcc-mcp-maya

# Maya 2025
"C:\Program Files\Autodesk\Maya2025\bin\mayapy.exe" -m pip install dcc-mcp-maya
```

If running multiple Maya instances simultaneously, use different ports:

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
