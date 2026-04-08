"""Maya userSetup.py — auto-load the dcc-mcp-maya plugin.

Copy this file to your Maya scripts directory:
  - Windows:  %USERPROFILE%/Documents/maya/scripts/userSetup.py
  - macOS:    ~/Library/Preferences/Autodesk/maya/scripts/userSetup.py
  - Linux:    ~/maya/scripts/userSetup.py

Or ``source`` it from your existing ``userSetup.py``.
"""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging

logger = logging.getLogger(__name__)


def _load_dcc_mcp_maya():
    try:
        import maya.cmds as cmds

        if not cmds.pluginInfo("dcc_mcp_maya", query=True, loaded=True):
            cmds.loadPlugin("dcc_mcp_maya", quiet=True)
            logger.info("dcc-mcp-maya plugin loaded via userSetup.py")
    except Exception as exc:
        logger.warning("dcc-mcp-maya auto-load failed: %s", exc)


try:
    import maya.utils

    maya.utils.executeDeferred(_load_dcc_mcp_maya)
except ImportError:
    pass
