DCC-MCP-Maya — Pipeline Deployment
====================================

This package is designed for network-share deployment in pipeline
environments. No install scripts are included.

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

Configuration
-------------
Environment variables (optional):

  DCC_MCP_MAYA_PORT        TCP port for the MCP server. Default: 0 (OS-assigned)
  DCC_MCP_MAYA_SERVER_NAME Server name in MCP initialize. Default: maya-mcp
  DCC_MCP_GATEWAY_PORT     Gateway port. Default: 9765
  DCC_MCP_MAYA_SKILL_PATHS Additional skill search paths (; separated)
  DCC_MCP_SKILL_PATHS      Global skill search paths (; separated)

For more information: https://github.com/loonghao/dcc-mcp-maya
