#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
MODULE_DIR="$SCRIPT_DIR/dcc-mcp-maya"

echo "========================================="
echo " DCC-MCP-Maya Installer"
echo "========================================="
echo

if [ ! -f "$MODULE_DIR/module-info.json" ]; then
    echo "ERROR: Module directory not found at:"
    echo "  $MODULE_DIR"
    echo
    echo "Please ensure this script is in the same directory as the dcc-mcp-maya folder."
    exit 1
fi

# Read version from module-info.json
VERSION=$(python3 -c "
import json, sys
with open('$MODULE_DIR/module-info.json') as f:
    print(json.load(f)['version'])
" 2>/dev/null || echo "unknown")
echo " Version: ${VERSION}"

# Check if python37/ exists (cp37 for Maya 2022)
HAS_CP37=0
if [ -d "$MODULE_DIR/python37" ]; then
    HAS_CP37=1
    echo " Python 3.7 support: Yes (Maya 2022)"
else
    echo " Python 3.7 support: No"
fi
echo

# Detect Maya installations
FOUND_MAYA=0
for year in 2026 2025 2024 2023 2022; do
    CANDIDATES=(
        "/usr/autodesk/maya${year}/bin/mayapy"
        "/Applications/Autodesk/maya${year}/Maya.app/Contents/bin/mayapy"
    )
    for c in "${CANDIDATES[@]}"; do
        if [ -x "$c" ]; then
            echo " Found Maya ${year} at $c"
            FOUND_MAYA=1
            break
        fi
    done
done
if [ "$FOUND_MAYA" -eq 0 ]; then
    echo " WARNING: No Maya installation detected."
    echo " The module will still be installed but Maya may not find it automatically."
    echo
fi

# Determine platform-specific paths and .mod platform string
if [[ "$OSTYPE" == "darwin"* ]]; then
    MOD_DEST="$HOME/Library/Preferences/Autodesk/maya/modules"
    SCRIPTS_DEST="$HOME/Library/Preferences/Autodesk/maya/scripts"
    PLATFORM="macos"
else
    MOD_DEST="$HOME/maya/modules"
    SCRIPTS_DEST="$HOME/maya/scripts"
    PLATFORM="linux"
fi

# Deploy module directory
mkdir -p "$MOD_DEST"

if [ -d "$MOD_DEST/dcc-mcp-maya" ]; then
    echo "Removing previous installation..."
    rm -rf "$MOD_DEST/dcc-mcp-maya"
fi

echo
echo "Deploying module to: $MOD_DEST/dcc-mcp-maya"
cp -R "$MODULE_DIR" "$MOD_DEST/dcc-mcp-maya"

# Generate .mod file dynamically
echo "Generating dcc_mcp_maya.mod..."
MOD_FILE="$MOD_DEST/dcc-mcp-maya/dcc_mcp_maya.mod"

{
    if [ "$HAS_CP37" -eq 1 ]; then
        echo "+ MAYAVERSION:2022 PLATFORM:$PLATFORM dcc_mcp_maya $VERSION ."
        echo "PYTHONPATH+:=python37"
        echo "PLUG_IN_PATH+:=plug-ins"
    fi
    for year in 2023 2024 2025 2026; do
        echo "+ MAYAVERSION:$year PLATFORM:$PLATFORM dcc_mcp_maya $VERSION ."
        echo "PYTHONPATH+:=python"
        echo "PLUG_IN_PATH+:=plug-ins"
    done
} > "$MOD_FILE"

echo " Generated $MOD_FILE"

# Deploy userSetup.py
mkdir -p "$SCRIPTS_DEST"

USERSETUP_DEST="$SCRIPTS_DEST/userSetup.py"
if [ ! -f "$USERSETUP_DEST" ]; then
    cp "$MOD_DEST/dcc-mcp-maya/scripts/userSetup.py" "$USERSETUP_DEST"
    echo "Deployed userSetup.py to $SCRIPTS_DEST"
else
    if ! grep -q "dcc_mcp_maya" "$USERSETUP_DEST" 2>/dev/null; then
        echo
        echo "Appending dcc-mcp-maya loader to existing userSetup.py..."
        cat >> "$USERSETUP_DEST" << 'USERSETUP_EOF'

# dcc-mcp-maya auto-load
try:
    import maya.utils
    def _load_dcc_mcp_maya():
        try:
            import maya.cmds as cmds
            if not cmds.pluginInfo("dcc_mcp_maya", query=True, loaded=True):
                cmds.loadPlugin("dcc_mcp_maya", quiet=True)
        except Exception:
            pass
    maya.utils.executeDeferred(_load_dcc_mcp_maya)
except ImportError:
    pass
USERSETUP_EOF
    else
        echo "userSetup.py already contains dcc-mcp-maya loader, skipping."
    fi
fi

echo
echo "========================================="
echo " Installation complete!"
echo
echo " Module:   $MOD_DEST/dcc-mcp-maya"
echo " Plugin:   $MOD_DEST/dcc-mcp-maya/plug-ins/dcc_mcp_maya.py"
echo

# Post-install verification
echo "Running post-install verification..."
VERIFY_MAYAPY=""
for year in 2026 2025 2024 2023 2022; do
    CANDIDATES=(
        "/usr/autodesk/maya${year}/bin/mayapy"
        "/Applications/Autodesk/maya${year}/Maya.app/Contents/bin/mayapy"
    )
    for c in "${CANDIDATES[@]}"; do
        if [ -x "$c" ]; then
            VERIFY_MAYAPY="$c"
            break 2
        fi
    done
done

if [ -n "$VERIFY_MAYAPY" ]; then
    echo "Using mayapy: $VERIFY_MAYAPY"
    if "$VERIFY_MAYAPY" "$MOD_DEST/dcc-mcp-maya/post_install.py"; then
        echo
        echo "Post-install verification: PASSED"
    else
        echo
        echo "WARNING: Post-install verification failed."
        echo "The module files are deployed but may not work correctly."
    fi
else
    echo "WARNING: No mayapy found — skipping post-install verification."
    echo "To verify manually, run:"
    echo "  mayapy $MOD_DEST/dcc-mcp-maya/post_install.py"
fi

echo
echo " The plugin will auto-load when Maya starts."
echo " Alternatively, load it via:"
echo "   Window > Settings/Preferences > Plug-in Manager"
echo "========================================="
