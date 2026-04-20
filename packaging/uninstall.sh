#!/usr/bin/env bash
set -e

echo "========================================="
echo " DCC-MCP-Maya Uninstaller"
echo "========================================="
echo

# Determine platform-specific paths
if [[ "$OSTYPE" == "darwin"* ]]; then
    MOD_FILE="$HOME/Library/Preferences/Autodesk/maya/modules/dcc_mcp_maya.mod"
    SCRIPTS_DIR="$HOME/Library/Preferences/Autodesk/maya/scripts"
else
    MOD_FILE="$HOME/maya/modules/dcc_mcp_maya.mod"
    SCRIPTS_DIR="$HOME/maya/scripts"
fi

if [ ! -f "$MOD_FILE" ]; then
    echo ".mod file not found at: $MOD_FILE"
    echo "Nothing to uninstall."
    exit 0
fi

echo "Removing .mod file: $MOD_FILE"
rm -f "$MOD_FILE"

echo
echo ".mod file removed successfully. The plugin will no longer load at Maya startup."
echo
echo "NOTE: The module directory was not deleted (it remains where you extracted it)."
echo "NOTE: userSetup.py was not modified. If you want to remove the"
echo "auto-load snippet, edit this file manually:"
echo "  $SCRIPTS_DIR/userSetup.py"
