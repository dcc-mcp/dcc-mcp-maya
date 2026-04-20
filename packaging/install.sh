#!/usr/bin/env bash
set -e

# -- Resolve module directory (this script lives inside it) --
MODULE_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "========================================="
echo " DCC-MCP-Maya Installer"
echo "========================================="
echo

# -- Read version from pre-generated .mod file --
VERSION=$(grep -m1 '^+ MAYAVERSION' "$MODULE_DIR/dcc_mcp_maya.mod" | awk '{print $4}')
VERSION="${VERSION:-unknown}"
echo " Version: ${VERSION}"
echo " Module:  ${MODULE_DIR}"
echo

# -- Determine platform-specific paths --
if [[ "$OSTYPE" == "darwin"* ]]; then
    MOD_DEST="$HOME/Library/Preferences/Autodesk/maya/modules"
    SCRIPTS_DEST="$HOME/Library/Preferences/Autodesk/maya/scripts"
    PLATFORM="macos"
else
    MOD_DEST="$HOME/maya/modules"
    SCRIPTS_DEST="$HOME/maya/scripts"
    PLATFORM="linux"
fi

# -- Generate .mod with absolute path to Maya modules dir --
mkdir -p "$MOD_DEST"

HAS_CP37=0
if [ -d "$MODULE_DIR/python37" ]; then
    HAS_CP37=1
fi

{
    if [ "$HAS_CP37" -eq 1 ]; then
        echo "+ MAYAVERSION:2022 PLATFORM:$PLATFORM dcc_mcp_maya $VERSION $MODULE_DIR"
        echo "PYTHONPATH+:=python37"
        echo "PLUG_IN_PATH+:=plug-ins"
    fi
    for year in 2023 2024 2025 2026; do
        echo "+ MAYAVERSION:$year PLATFORM:$PLATFORM dcc_mcp_maya $VERSION $MODULE_DIR"
        echo "PYTHONPATH+:=python"
        echo "PLUG_IN_PATH+:=plug-ins"
    done
} > "$MOD_DEST/dcc_mcp_maya.mod"

echo " Generated $MOD_DEST/dcc_mcp_maya.mod"

# -- Deploy userSetup.py --
mkdir -p "$SCRIPTS_DEST"

USERSETUP_DEST="$SCRIPTS_DEST/userSetup.py"
if [ ! -f "$USERSETUP_DEST" ]; then
    cp "$MODULE_DIR/scripts/userSetup.py" "$USERSETUP_DEST"
    echo " Deployed userSetup.py"
else
    if ! grep -q "dcc_mcp_maya" "$USERSETUP_DEST" 2>/dev/null; then
        echo "" >> "$USERSETUP_DEST"
        cat "$MODULE_DIR/scripts/userSetup.py" >> "$USERSETUP_DEST"
        echo " Appended to existing userSetup.py"
    else
        echo " userSetup.py already configured, skipping."
    fi
fi

echo
echo "========================================="
echo " Installation complete!"
echo
echo " .mod file:  $MOD_DEST/dcc_mcp_maya.mod"
echo " Module:     $MODULE_DIR"
echo " Plugin:     $MODULE_DIR/plug-ins/dcc_mcp_maya_plugin.py"
echo
echo " The plugin will auto-load when Maya starts."
echo "========================================="
