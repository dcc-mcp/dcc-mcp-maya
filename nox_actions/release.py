# Import built-in modules
import argparse
import os
import shutil
import subprocess
import zipfile
from pathlib import Path

# Import third-party modules
import nox
from nox_actions.utils import PACKAGE_NAME
from nox_actions.utils import THIS_ROOT

# ── Install script templates ────────────────────────────────────────────────

_BAT_TEMPLATE = r"""@echo off
setlocal

echo =========================================
echo  DCC-MCP-Maya Installer
echo  Version: {version}
echo =========================================
echo.

REM -- Detect mayapy --
set MAYAPY=""
for %%Y in (2026 2025 2024 2023 2022) do (
    if exist "C:\Program Files\Autodesk\Maya%%Y\bin\mayapy.exe" (
        set MAYAPY="C:\Program Files\Autodesk\Maya%%Y\bin\mayapy.exe"
        echo Found Maya %%Y
        goto :found
    )
)
echo ERROR: Could not find Maya installation. Please install manually.
pause & exit /b 1

:found
echo Installing Python dependencies into Maya...
%MAYAPY% -m pip install --no-index --find-links="%~dp0packages" ^
    dcc-mcp-core dcc-mcp-ipc rpyc fastmcp 2>nul
if errorlevel 1 (
    echo Falling back to online install...
    %MAYAPY% -m pip install dcc-mcp-core>={dcc_mcp_core_version} dcc-mcp-ipc>={dcc_mcp_ipc_version} rpyc>=6.0.0 fastmcp>=2.0.0
)

echo.
echo Deploying Maya plugin...
set PLUGIN_DEST=%USERPROFILE%\Documents\maya\plug-ins
if not exist "%PLUGIN_DEST%" mkdir "%PLUGIN_DEST%"
copy /y "%~dp0maya\plugin\dcc_mcp_maya.py" "%PLUGIN_DEST%\dcc_mcp_maya.py"

echo Deploying userSetup.py...
set SCRIPTS_DEST=%USERPROFILE%\Documents\maya\scripts
if not exist "%SCRIPTS_DEST%" mkdir "%SCRIPTS_DEST%"

REM Append userSetup content rather than overwrite
set USERSETUP_SRC=%~dp0maya\userSetup.py
set USERSETUP_DEST=%SCRIPTS_DEST%\userSetup.py
if not exist "%USERSETUP_DEST%" (
    copy /y "%USERSETUP_SRC%" "%USERSETUP_DEST%"
) else (
    echo userSetup.py already exists, skipping (add manually if needed).
)

echo.
echo =========================================
echo  Installation complete!
echo  Plugin: %PLUGIN_DEST%\dcc_mcp_maya.py
echo  Load it in Maya: Plug-in Manager
echo =========================================
pause
endlocal
"""

_SH_TEMPLATE = """#!/usr/bin/env bash
set -e

VERSION="{version}"
DCC_MCP_CORE_VERSION="{dcc_mcp_core_version}"
DCC_MCP_IPC_VERSION="{dcc_mcp_ipc_version}"

echo "========================================="
echo " DCC-MCP-Maya Installer v${{VERSION}}"
echo "========================================="

# Detect mayapy
MAYAPY=""
for year in 2026 2025 2024 2023 2022; do
    CANDIDATES=(
        "/usr/autodesk/maya${{year}}/bin/mayapy"
        "/Applications/Autodesk/maya${{year}}/Maya.app/Contents/bin/mayapy"
    )
    for c in "${{CANDIDATES[@]}}"; do
        if [ -x "$c" ]; then
            MAYAPY="$c"
            echo "Found Maya ${{year}} at $c"
            break 2
        fi
    done
done

if [ -z "$MAYAPY" ]; then
    echo "ERROR: Could not find mayapy. Set MAYAPY env var manually."
    echo "  export MAYAPY=/path/to/mayapy && bash install.sh"
    exit 1
fi

echo "Installing Python dependencies..."
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

$MAYAPY -m pip install --no-index --find-links="$SCRIPT_DIR/packages" \\
    dcc-mcp-core dcc-mcp-ipc rpyc fastmcp 2>/dev/null || \\
$MAYAPY -m pip install \\
    "dcc-mcp-core>=$DCC_MCP_CORE_VERSION" \\
    "dcc-mcp-ipc>=$DCC_MCP_IPC_VERSION" \\
    "rpyc>=6.0.0" \\
    "fastmcp>=2.0.0"

echo "Deploying Maya plugin..."
if [[ "$OSTYPE" == "darwin"* ]]; then
    PLUGIN_DEST="$HOME/Library/Preferences/Autodesk/maya/plug-ins"
    SCRIPTS_DEST="$HOME/Library/Preferences/Autodesk/maya/scripts"
else
    PLUGIN_DEST="$HOME/maya/plug-ins"
    SCRIPTS_DEST="$HOME/maya/scripts"
fi

mkdir -p "$PLUGIN_DEST" "$SCRIPTS_DEST"
cp -f "$SCRIPT_DIR/maya/plugin/dcc_mcp_maya.py" "$PLUGIN_DEST/dcc_mcp_maya.py"

if [ ! -f "$SCRIPTS_DEST/userSetup.py" ]; then
    cp -f "$SCRIPT_DIR/maya/userSetup.py" "$SCRIPTS_DEST/userSetup.py"
else
    echo "userSetup.py already exists, skipping (add manually if needed)."
fi

echo ""
echo "========================================="
echo " Installation complete!"
echo " Plugin: $PLUGIN_DEST/dcc_mcp_maya.py"
echo " Load it in Maya: Plug-in Manager"
echo "========================================="
"""

_START_SERVER_BAT = r"""@echo off
REM Start the DCC-MCP-Maya MCP HTTP server (standalone, outside Maya)
echo Starting DCC-MCP-Maya MCP HTTP server...
set SCRIPT_DIR=%~dp0
python "%SCRIPT_DIR%mcp_server\run_server.py" %*
pause
"""

_START_SERVER_SH = """#!/usr/bin/env bash
# Start the DCC-MCP-Maya MCP HTTP server (standalone, outside Maya)
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
echo "Starting DCC-MCP-Maya MCP HTTP server..."
python "$SCRIPT_DIR/mcp_server/run_server.py" "$@"
"""

# ── Versions to embed in scripts ────────────────────────────────────────────
_DEP_VERSIONS = {
    "dcc_mcp_core_version": "0.12.0",
    "dcc_mcp_ipc_version": "2.0.0",
}


def make_install_zip(session: nox.Session) -> None:
    """Create a standalone distributable ZIP for Maya.

    The ZIP contains:
    - install.bat / install.sh  (one-click installer)
    - start_mcp_server.bat / .sh  (launch the MCP HTTP server)
    - maya/plugin/dcc_mcp_maya.py
    - maya/userSetup.py
    - mcp_server/run_server.py
    - src/dcc_mcp_maya/  (the Python package)

    Usage:
        nox -s make-zip -- --version 0.1.0
    """
    parser = argparse.ArgumentParser(prog="nox -s make-zip")
    parser.add_argument("--version", default="0.1.0", help="Release version string")
    args = parser.parse_args(session.posargs)
    version = str(args.version)
    print(f"Building install zip for version: {version}")

    # ── Build directory setup ──
    temp_dir = THIS_ROOT / ".zip"
    build_root = temp_dir / PACKAGE_NAME
    shutil.rmtree(temp_dir, ignore_errors=True)
    build_root.mkdir(parents=True)

    tmpl_vars = {"version": version, **_DEP_VERSIONS}

    # ── Write installer scripts ──
    (build_root / "install.bat").write_text(_BAT_TEMPLATE.format(**tmpl_vars))
    sh_path = build_root / "install.sh"
    sh_path.write_text(_SH_TEMPLATE.format(**tmpl_vars))

    # ── Write server launcher scripts ──
    (build_root / "start_mcp_server.bat").write_text(_START_SERVER_BAT)
    srv_sh = build_root / "start_mcp_server.sh"
    srv_sh.write_text(_START_SERVER_SH)

    def _ignore(dir_, names):
        return [n for n in names if n in ("__pycache__", ".pytest_cache") or n.endswith(".pyc")]

    # ── Copy Maya plugin files ──
    maya_dst = build_root / "maya"
    shutil.copytree(THIS_ROOT / "maya", maya_dst, ignore=_ignore)

    # ── Copy Python package ──
    src_dst = build_root / "src" / "dcc_mcp_maya"
    shutil.copytree(THIS_ROOT / "src" / "dcc_mcp_maya", src_dst, ignore=_ignore)

    # ── Copy MCP server ──
    mcp_server_src = THIS_ROOT / "mcp_server"
    if mcp_server_src.exists():
        shutil.copytree(mcp_server_src, build_root / "mcp_server", ignore=_ignore)

    # ── Create the final ZIP ──
    zip_file = temp_dir / f"{PACKAGE_NAME}-{version}.zip"
    with zipfile.ZipFile(zip_file, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(build_root):
            dirs[:] = [d for d in dirs if d not in ("__pycache__", ".pytest_cache")]
            for file in files:
                if file.endswith(".pyc"):
                    continue
                abs_path = Path(root) / file
                arc_name = abs_path.relative_to(build_root)
                zf.write(abs_path, arc_name)

    print(f"Created: {zip_file}")
    print(f"Contents:")
    with zipfile.ZipFile(zip_file) as zf:
        for name in sorted(zf.namelist()):
            print(f"  {name}")
