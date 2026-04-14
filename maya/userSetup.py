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
import os
import sys
from pathlib import Path

logger = logging.getLogger(__name__)


def _setup_module_paths() -> None:
    """Ensure .mod module paths are on sys.path and MAYA_PLUG_IN_PATH.

    Maya GUI mode processes ``.mod`` files and adds their ``PYTHONPATH+:=...``
    and ``PLUG_IN_PATH+:=...`` entries automatically.  However, Maya standalone
    and batch modes **do not** process these directives.

    This helper scans the standard Maya module directories for the
    ``dcc-mcp-maya`` module and configures both ``sys.path`` (for Python
    package imports) and ``MAYA_PLUG_IN_PATH`` (for ``cmds.loadPlugin``) so
    the plugin works in all Maya modes.
    """
    # If dcc_mcp_maya is already importable, nothing to do
    try:
        import dcc_mcp_maya  # noqa: F401

        return
    except ImportError:
        pass

    # Standard Maya module directories (per-platform)
    if sys.platform == "win32":
        module_dirs = [
            Path(os.environ.get("USERPROFILE", "")) / "Documents" / "maya" / "modules",
        ]
    elif sys.platform == "darwin":
        module_dirs = [
            Path.home() / "Library" / "Preferences" / "Autodesk" / "maya" / "modules",
        ]
    else:
        module_dirs = [
            Path.home() / "maya" / "modules",
        ]

    for mod_dir in module_dirs:
        module_root = mod_dir / "dcc-mcp-maya"
        if not module_root.is_dir():
            continue

        # Add plug-ins/ to MAYA_PLUG_IN_PATH so loadPlugin can find the .py
        plugins_dir = module_root / "plug-ins"
        if plugins_dir.is_dir():
            current = os.environ.get("MAYA_PLUG_IN_PATH", "")
            plugins_str = str(plugins_dir)
            if plugins_str not in current:
                sep = ";" if sys.platform == "win32" else ":"
                os.environ["MAYA_PLUG_IN_PATH"] = f"{plugins_str}{sep}{current}" if current else plugins_str

        # Determine which python/ subdir to use based on Maya version
        try:
            import maya.cmds as _cmds  # noqa: PLC0415

            maya_version = _cmds.about(version=True)
            major = int(str(maya_version).split(".")[0])
        except Exception:
            major = 2025

        python_dir = module_root / "python37" if major == 2022 else module_root / "python"
        if not python_dir.is_dir():
            python_dir = module_root / "python"

        python_str = str(python_dir)
        if python_dir.is_dir() and python_str not in sys.path:
            sys.path.insert(0, python_str)
            logger.debug("Added %s to sys.path for dcc-mcp-maya", python_str)

        # One module root found — done
        break


def _load_dcc_mcp_maya():
    try:
        import maya.cmds as cmds

        _setup_module_paths()

        if not cmds.pluginInfo("dcc_mcp_maya_plugin", query=True, loaded=True):
            cmds.loadPlugin("dcc_mcp_maya_plugin", quiet=True)
            logger.info("dcc-mcp-maya plugin loaded via userSetup.py")
    except Exception as exc:
        logger.warning("dcc-mcp-maya auto-load failed: %s", exc)


try:
    import maya.utils

    maya.utils.executeDeferred(_load_dcc_mcp_maya)
except ImportError:
    pass
