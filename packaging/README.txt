DCC-MCP-Maya — Maya Module Distribution
========================================

Offline Maya .mod module package. Contains the MCP Streamable HTTP
server plugin and all Python dependencies (including dcc-mcp-core).

Requirements
------------
- Autodesk Maya 2022, 2023, 2024, or 2025 (matching platform ZIP)

Installation
------------
1. Unzip the archive.
2. Double-click install.bat (Windows) or run install.sh (Linux/macOS).
3. Start Maya — the plugin loads automatically via userSetup.py.

Alternatively, load manually via:
  Window > Settings/Preferences > Plug-in Manager > dcc_mcp_maya

Uninstallation
--------------
Double-click uninstall.bat (Windows) or run uninstall.sh (Linux/macOS).

Configuration
-------------
Environment variables (optional):

  DCC_MCP_MAYA_PORT        TCP port for the MCP server. Default: 8765
  DCC_MCP_MAYA_SERVER_NAME Server name in MCP initialize. Default: maya-mcp
  DCC_MCP_MAYA_SKILL_PATHS Additional skill search paths (; separated)
  DCC_MCP_SKILL_PATHS      Global skill search paths (; separated)

Troubleshooting
---------------
- If the plugin does not appear in Plug-in Manager, verify the module
  directory is at: <User Documents>/maya/modules/dcc-mcp-maya/
- Check the Maya Script Editor output window for error messages.
- Ensure the ZIP matches your platform (win64 / linux / macos).

For more information: https://github.com/loonghao/dcc-mcp-maya
