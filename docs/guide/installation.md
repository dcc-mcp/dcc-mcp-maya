# Installation

Detailed installation instructions for all supported Maya versions.

## Requirements

| Maya Version | Python | Status |
|---|---|---|
| Maya 2026 | 3.11 | ✅ Fully supported |
| Maya 2025 | 3.11 | ✅ Fully supported |
| Maya 2024 | 3.10 | ✅ Fully supported |
| Maya 2023 | 3.9 | ✅ Fully supported |
| Maya 2022 | 3.7 | ✅ Supported |
| Maya 2020 | 3.7 | ✅ Supported |

## Method 1: pip into mayapy (Recommended)

This is the simplest method. It installs `dcc-mcp-maya` into Maya's own Python environment.

### Windows

```powershell
# Default Maya 2026 location
& "C:\Program Files\Autodesk\Maya2026\bin\mayapy.exe" -m pip install dcc-mcp-maya

# Or if mayapy is on PATH
mayapy -m pip install dcc-mcp-maya
```

### macOS

```bash
/Applications/Autodesk/maya2026/Maya.app/Contents/bin/mayapy -m pip install dcc-mcp-maya
```

### Linux

```bash
/usr/autodesk/maya2026/bin/mayapy -m pip install dcc-mcp-maya
```

### Upgrading

```bash
mayapy -m pip install --upgrade dcc-mcp-maya
```

### Verifying the Installation

```bash
mayapy -c "import dcc_mcp_maya; print(dcc_mcp_maya.__version__)"
```

## Method 2: Maya Plugin

Load the server as a Maya plugin for automatic startup.

### Setup

1. Copy `maya/plugin/dcc_mcp_maya.py` from the repository to a directory on `MAYA_PLUG_IN_PATH`.

   Common paths:
   - Windows: `%USERPROFILE%\Documents\maya\2026\plug-ins\`
   - macOS: `~/Library/Preferences/Autodesk/maya/2026/plug-ins/`
   - Linux: `~/maya/2026/plug-ins/`

2. In Maya: **Window > Settings/Preferences > Plug-in Manager**

3. Find `dcc_mcp_maya` in the list and check **Loaded** (and optionally **Auto load**).

The server starts automatically when the plugin loads on port `8765` (or the value of `DCC_MCP_MAYA_PORT`).

## Method 3: userSetup.py Auto-start

For a lightweight setup without the plugin:

```python
# ~/maya/scripts/userSetup.py
import maya.utils

def _start_mcp_server():
    try:
        import dcc_mcp_maya
        handle = dcc_mcp_maya.start_server(port=8765)
        print(f"[dcc-mcp-maya] Server ready at {handle.mcp_url()}")
    except Exception as e:
        print(f"[dcc-mcp-maya] Failed to start: {e}")

maya.utils.executeDeferred(_start_mcp_server)
```

## Installing in a Specific Maya Version

If you have multiple Maya versions:

```bash
# Maya 2024
"C:\Program Files\Autodesk\Maya2024\bin\mayapy.exe" -m pip install dcc-mcp-maya

# Maya 2025
"C:\Program Files\Autodesk\Maya2025\bin\mayapy.exe" -m pip install dcc-mcp-maya
```

Each Maya version has its own Python environment.

## Offline / Air-gapped Installation

Download the wheel first on a connected machine:

```bash
pip download dcc-mcp-maya --dest ./offline-pkgs
```

Then install on the offline machine:

```bash
mayapy -m pip install --no-index --find-links ./offline-pkgs dcc-mcp-maya
```

## Dependencies

`dcc-mcp-maya` has a single runtime dependency:

| Package | Version | Purpose |
|---------|---------|---------|
| `dcc-mcp-core` | `>=0.12.12,<1.0.0` | MCP server, action registry, skill catalog |

`dcc-mcp-core` includes a compiled Rust/Tokio HTTP server (`axum`) distributed as a Python wheel. No additional system dependencies are required.

## Uninstalling

```bash
mayapy -m pip uninstall dcc-mcp-maya
```
