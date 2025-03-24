# Import built-in modules
import argparse
import os
import shutil
import sys
import zipfile
from pathlib import Path

# Import third-party modules
import nox

# Import local modules
from nox_actions.utils import THIS_ROOT


def make_maya_install_zip(session):
    """Create an installation ZIP file for the Maya MCP plugin.

    This function creates a ZIP file containing the Maya MCP plugin and all necessary files
    for installation in Maya. The ZIP file includes:
    - The Maya MCP plugin files
    - Installation scripts
    - Module file template
    - README file

    Args:
        session: The nox session object

    Returns:
        Path to the created ZIP file
    """
    # Parse arguments
    parser = argparse.ArgumentParser()
    parser.add_argument("--version", default="0.1.0", help="Version to use for the zip file")
    parser.add_argument("--include-deps", action="store_true", help="Include dependencies in the package")

    # Parse arguments from session.posargs or sys.argv if running directly
    if hasattr(session, "posargs") and session.posargs:
        args = parser.parse_args(session.posargs)
    elif __name__ == "__main__":
        args = parser.parse_args()
    else:
        args = parser.parse_args([])

    version = args.version
    include_deps = args.include_deps

    print(f"Making Maya MCP plugin zip for version: {version}")
    print(f"Include dependencies: {include_deps}")

    # Create temporary directory structure
    temp_dir = os.path.join(THIS_ROOT, ".zip")
    build_root = os.path.join(temp_dir, "maya_mcp")
    scripts_dir = os.path.join(build_root, "scripts")
    plugin_dir = os.path.join(scripts_dir, "maya_mcp", "plugin")
    actions_dir = os.path.join(scripts_dir, "maya_mcp", "actions")
    site_packages_dir = os.path.join(scripts_dir, "site-packages")

    # Clean previous build
    shutil.rmtree(temp_dir, ignore_errors=True)
    os.makedirs(build_root, exist_ok=True)
    os.makedirs(scripts_dir, exist_ok=True)
    os.makedirs(plugin_dir, exist_ok=True)
    os.makedirs(actions_dir, exist_ok=True)
    if include_deps:
        os.makedirs(site_packages_dir, exist_ok=True)

    # Get maya directory path
    maya_dir = os.path.join(THIS_ROOT, "maya")
    if not os.path.exists(maya_dir):
        print(f"Warning: Maya directory {maya_dir} not found")
        return None

    # Copy README.md to build_root
    readme_path = os.path.join(maya_dir, "README.md")
    if os.path.exists(readme_path):
        shutil.copy2(readme_path, os.path.join(build_root, "README.md"))
        print(f"Copied README.md to {build_root}")

    # Copy userSetup.py to scripts_dir
    usersetup_path = os.path.join(maya_dir, "userSetup.py")
    if os.path.exists(usersetup_path):
        shutil.copy2(usersetup_path, os.path.join(scripts_dir, "userSetup.py"))
        print(f"Copied userSetup.py to {scripts_dir}")
    else:
        print(f"Warning: userSetup.py not found in {maya_dir}")

    # Copy actions directory contents to actions_dir
    actions_src = os.path.join(maya_dir, "actions")
    if os.path.exists(actions_src):
        for item in os.listdir(actions_src):
            src_item = os.path.join(actions_src, item)
            dst_item = os.path.join(actions_dir, item)
            if os.path.isfile(src_item):
                shutil.copy2(src_item, dst_item)
            elif os.path.isdir(src_item):
                shutil.copytree(src_item, dst_item)
        print(f"Copied actions files from {actions_src} to {actions_dir}")
    else:
        print(f"Warning: Actions directory {actions_src} not found")

    # Copy plugin files to plugin_dir
    plugin_src = os.path.join(maya_dir, "plugin")
    if os.path.exists(plugin_src):
        for item in os.listdir(plugin_src):
            src_item = os.path.join(plugin_src, item)
            dst_item = os.path.join(plugin_dir, item)
            if os.path.isfile(src_item):
                shutil.copy2(src_item, dst_item)
            elif os.path.isdir(src_item):
                shutil.copytree(src_item, dst_item)
        print(f"Copied plugin files from {plugin_src} to {plugin_dir}")
    else:
        print(f"Warning: Plugin directory {plugin_src} not found")

    # Include dependencies if requested
    if include_deps:
        # For now, we'll just create a README file explaining how to install dependencies
        with open(os.path.join(site_packages_dir, "README.txt"), "w") as f:
            f.write("""
Dependencies:

This plugin requires the following dependencies:
- dcc-mcp-rpyc

You can install them using pip:
    pip install dcc-mcp-rpyc

Or copy the packages to the site-packages directory.
""")
        print("Created dependency README in site-packages directory")

    # Create install.bat
    bat_template = """
@echo off
SET "batPath=%~dp0"
SET "modContent=+ maya_mcp {version} %batPath%"
SET "modFilePath=%~dp0maya_mcp.mod"
echo %modContent% > "%modFilePath%"

REM Check if target directory exists, if not, create it
IF NOT EXIST "%USERPROFILE%\documents\maya\modules\" (
    echo Creating directory: %USERPROFILE%\documents\maya\modules\
    mkdir "%USERPROFILE%\documents\maya\modules\"
)

REM Use /i parameter to tell xcopy that the destination is a directory
xcopy "%~dp0maya_mcp.mod" "%USERPROFILE%\documents\maya\modules\" /y /i

del /f "%~dp0maya_mcp.mod"
echo Installation completed! Maya MCP plugin successfully installed to %USERPROFILE%\documents\maya\modules\
pause
"""
    with open(os.path.join(build_root, "install.bat"), "w") as f:
        f.write(bat_template.format(version=version))

    # Create module file
    mod_template = """+ maya_mcp {version} .\n"""
    with open(os.path.join(build_root, "maya_mcp.mod.template"), "w") as f:
        f.write(mod_template.format(version=version))

    # Create zip file
    zip_file = os.path.join(temp_dir, f"maya_mcp-{version}.zip")
    with zipfile.ZipFile(zip_file, "w") as zip_obj:
        for root, _, files in os.walk(build_root):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, os.path.join(build_root, "."))
                zip_obj.write(file_path, arcname)

    print(f"Maya MCP plugin zip created: {zip_file}")
    return zip_file


@nox.session(python=False, name="make-maya-zip")
def make_maya_zip(session: nox.Session) -> None:
    """Create a Maya MCP plugin ZIP package.

    Args:
        session: The nox session object

    """
    make_maya_install_zip(session)
