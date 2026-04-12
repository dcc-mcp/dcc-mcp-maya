#!/usr/bin/env bash
set -e

echo "========================================="
echo " DCC-MCP-Maya Uninstaller"
echo "========================================="
echo

# Determine platform-specific paths
if [[ "$OSTYPE" == "darwin"* ]]; then
    MOD_DEST="$HOME/Library/Preferences/Autodesk/maya/modules/dcc-mcp-maya"
else
    MOD_DEST="$HOME/maya/modules/dcc-mcp-maya"
fi

if [ ! -d "$MOD_DEST" ]; then
    echo "Module directory not found at: $MOD_DEST"
    echo "Nothing to uninstall."
    exit 0
fi

echo "Removing module directory: $MOD_DEST"
rm -rf "$MOD_DEST"

echo
echo "Module removed successfully."
echo
echo "NOTE: userSetup.py was not modified. If you want to remove the"
echo "auto-load snippet, edit this file manually:"
if [[ "$OSTYPE" == "darwin"* ]]; then
    echo "  ~/Library/Preferences/Autodesk/maya/scripts/userSetup.py"
else
    echo "  ~/maya/scripts/userSetup.py"
fi
