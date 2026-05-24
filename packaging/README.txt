DCC-MCP-Maya — Maya Module Distribution
========================================

Offline Maya .mod module package. Contains the MCP Streamable HTTP
server plugin and the Python dependencies needed by the in-process
Maya bridge (including dcc-mcp-core).

This ZIP does not bundle the external dcc-mcp-server sidecar binary.
Default plugin gateway mode needs that binary to be available from the
same environment that launches Maya.

Requirements
------------
- Autodesk Maya 2022, 2023, 2024, 2025, or 2026 (matching platform ZIP; Maya 2022 requires python37/, available in Windows/Linux packages)
- dcc-mcp-server >= 0.17.23 for default sidecar gateway mode, unless your studio provides the binary on PATH or via DCC_MCP_SERVER_BIN

Installation
------------
1. Unzip the archive to any location.
2. Open the extracted dcc-mcp-maya folder.
3. Double-click install.bat (Windows) or run install.sh (Linux/macOS).
4. Start Maya — the plugin loads automatically via userSetup.py.

The installer generates a .mod file pointing to the extracted location
and deploys userSetup.py to your Maya scripts directory. The module
files stay where you extracted them — only the .mod pointer is copied.

Sidecar runtime
---------------
Default plugin mode starts a dcc-mcp-server sidecar and exposes the
gateway at http://127.0.0.1:9765/mcp. Install or provide the sidecar
runtime before loading the plugin on a clean machine:

  mayapy -m pip install "dcc-mcp-server>=0.17.23"

Clean-machine verification:

  mayapy -c "from dcc_mcp_maya.sidecar import resolve_sidecar_binary; print(resolve_sidecar_binary())"

Alternative deployment options:

- Set DCC_MCP_SERVER_BIN to the full dcc-mcp-server executable path.
- Put dcc-mcp-server on PATH before launching Maya.
- Set DCC_MCP_MAYA_SIDECAR=0 before loading the plugin to use the
  legacy in-process gateway path instead.

Uninstallation
--------------
Double-click uninstall.bat (Windows) or run uninstall.sh (Linux/macOS).
This removes the .mod file from your Maya modules directory. The
extracted module folder is not deleted.

Alternatively, load manually via:
  Window > Settings/Preferences > Plug-in Manager > dcc_mcp_maya

Configuration
-------------
Environment variables (optional):

  DCC_MCP_MAYA_PORT        TCP port for the MCP server. Default: 0 (OS-assigned)
  DCC_MCP_MAYA_SERVER_NAME Server name in MCP initialize. Default: maya-mcp
  DCC_MCP_GATEWAY_PORT     Gateway port. Default: 9765
  DCC_MCP_MAYA_SIDECAR     0 disables the default sidecar process
  DCC_MCP_SERVER_BIN       Explicit path to the dcc-mcp-server binary
  DCC_MCP_MAYA_SKILL_PATHS Additional skill search paths (; separated)
  DCC_MCP_SKILL_PATHS      Global skill search paths (; separated)

Troubleshooting
---------------
- If the plugin does not appear in Plug-in Manager, verify the .mod
  file exists at: <User Documents>/maya/modules/dcc_mcp_maya.mod
- Check the Maya Script Editor output window for error messages.
- Ensure the ZIP matches your platform (win64 / linux / macos).

For more information: https://github.com/loonghao/dcc-mcp-maya
