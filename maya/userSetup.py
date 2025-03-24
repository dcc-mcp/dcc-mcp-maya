"""Maya userSetup script for DCC-MCP.

This script is automatically executed when Maya starts. It adds the Maya MCP plugin
to Maya's plugin path and loads it.
"""

import os
import maya.cmds as cmds


def setup_maya_mcp():
    """Set up the Maya MCP environment.

    This function adds the plugin directory to Maya's plugin path and loads the plugin.
    It also ensures the necessary Python modules are in the Python path.
    """
    # Get the directory of this script
    script_dir = os.path.dirname(os.path.abspath(__file__))

    # Add the plugin directory to Maya's plugin path
    plugin_dir = os.path.join(script_dir, "maya_mcp", "plugin")
    if not os.path.exists(plugin_dir):
        # Try alternative path for development environment
        plugin_dir = os.path.join(os.path.dirname(script_dir), "plugin")
        if not os.path.exists(plugin_dir):
            os.makedirs(plugin_dir)

    # Add the plugin directory to Maya's plugin path
    plugin_path = os.environ.get("MAYA_PLUG_IN_PATH", "")
    if plugin_dir not in plugin_path:
        os.environ["MAYA_PLUG_IN_PATH"] = os.pathsep.join([plugin_dir, plugin_path]) if plugin_path else plugin_dir

    # Try to load the plugin
    try:
        if not cmds.pluginInfo("maya_mcp.py", query=True, loaded=True):
            cmds.loadPlugin("maya_mcp.py")
            if not cmds.about(batch=True):
                cmds.inViewMessage(message="Successfully loaded <hl>Maya MCP</hl> plugin.", pos="topRight", fade=True)
            else:
                print("-----------------------Loading Maya MCP plugin successfully----------------------")
    except Exception as e:
        print(f"Error loading Maya MCP plugin: {e}")


# Execute the setup function after Maya has started
if __name__ == "__main__":
    cmds.evalDeferred(setup_maya_mcp)
