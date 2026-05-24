DCC-MCP-Maya — Pipeline Deployment
====================================

This package is designed for network-share deployment in pipeline
environments. No install scripts are included.

The module content includes the Maya plugin, dcc-mcp-maya Python
package, and the in-process bridge dependencies such as dcc-mcp-core.
It does not bundle the external dcc-mcp-server sidecar binary. Default
plugin gateway mode needs that binary to be available from the same
environment that launches Maya.

Deployment Options
------------------

Option A: MAYA_MODULE_PATH (recommended)
  Add the parent directory of this folder to MAYA_MODULE_PATH.
  The included dcc_mcp_maya.mod uses relative paths (.) so it
  works from any location.

  Example:
    set MAYA_MODULE_PATH=\\server\tools\dcc-mcp-maya-module;%MAYA_MODULE_PATH%

Option B: Maya modules directory
  Copy or symlink dcc_mcp_maya.mod to a Maya modules directory:
    - Windows:  %USERPROFILE%\Documents\maya\modules\
    - Linux:    ~/maya/modules/
    - macOS:    ~/Library/Preferences/Autodesk/maya/modules/

  IMPORTANT: The .mod file uses relative paths (.), so it must
  be in the same directory as the module content (plug-ins/,
  python/, scripts/), or you must edit the module path in the
  .mod file to point to the actual location.

userSetup.py
------------
To auto-load the plugin at Maya startup, copy scripts/userSetup.py
to your Maya scripts directory, or source it from your existing
userSetup.py.

Sidecar runtime
---------------
Default plugin mode starts a dcc-mcp-server sidecar and exposes the
gateway at http://127.0.0.1:9765/mcp. Provide dcc-mcp-server >= 0.17.23
for every Maya environment that consumes this network module.

Common deployment options:

- Install into each target mayapy:
    mayapy -m pip install "dcc-mcp-server>=0.17.23"
- Set DCC_MCP_SERVER_BIN to a centrally managed dcc-mcp-server path.
- Put dcc-mcp-server on PATH in the launcher that starts Maya.
- Set DCC_MCP_MAYA_SIDECAR=0 before loading the plugin to use the
  legacy in-process gateway path instead.

Clean-machine verification:

  mayapy -c "from dcc_mcp_maya.sidecar import resolve_sidecar_binary; print(resolve_sidecar_binary())"

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

For more information: https://github.com/loonghao/dcc-mcp-maya
