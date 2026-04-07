"""Maya userSetup.py — Auto-load the DCC-MCP plugin on startup.

Place this file (or append its content) in your Maya scripts directory:
    Windows: %USERPROFILE%/Documents/maya/<version>/scripts/
    macOS:   ~/Library/Preferences/Autodesk/maya/<version>/scripts/
    Linux:   ~/maya/<version>/scripts/

This auto-loads the dcc_mcp_maya plugin when Maya starts.
"""

# Import Maya modules
import maya.utils


def _load_dcc_mcp_plugin():
    import maya.cmds as cmds
    import logging
    logger = logging.getLogger("dcc_mcp_maya.userSetup")
    try:
        # Only auto-load if not already loaded
        if not cmds.pluginInfo("dcc_mcp_maya", query=True, loaded=True):
            cmds.loadPlugin("dcc_mcp_maya")
            logger.info("DCC-MCP Maya plugin auto-loaded via userSetup.py")
    except Exception as e:
        logger.warning("DCC-MCP auto-load failed (plugin may not be on MAYA_PLUG_IN_PATH): %s", e)


maya.utils.executeDeferred(_load_dcc_mcp_plugin)
