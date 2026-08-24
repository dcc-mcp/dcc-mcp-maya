"""Maya userSetup.py -- auto-load the receipted dcc-mcp-maya module."""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

logger = logging.getLogger(__name__)


def _setup_module_paths() -> None:
    """Expose the installed module in GUI, standalone, and batch modes."""
    try:
        import dcc_mcp_maya  # noqa: F401

        return
    except ImportError:
        pass

    if sys.platform == "win32":
        module_dirs = [Path(os.environ.get("USERPROFILE", "")) / "Documents" / "maya" / "modules"]
    elif sys.platform == "darwin":
        module_dirs = [Path.home() / "Library" / "Preferences" / "Autodesk" / "maya" / "modules"]
    else:
        module_dirs = [Path.home() / "maya" / "modules"]

    for modules_dir in module_dirs:
        module_root = modules_dir / "dcc-mcp-maya"
        if not module_root.is_dir():
            continue
        plugins_dir = module_root / "plug-ins"
        if plugins_dir.is_dir():
            current = os.environ.get("MAYA_PLUG_IN_PATH", "")
            plugins = str(plugins_dir)
            if plugins not in current.split(os.pathsep):
                os.environ["MAYA_PLUG_IN_PATH"] = plugins + (os.pathsep + current if current else "")
        python_dir = module_root / ("python37" if sys.version_info[:2] == (3, 7) else "python")
        if not python_dir.is_dir():
            python_dir = module_root / "python"
        python_path = str(python_dir)
        if python_dir.is_dir() and python_path not in sys.path:
            sys.path.insert(0, python_path)
        break


def _apply_default_env() -> None:
    os.environ.setdefault("DCC_MCP_MAYA_PORT", "0")
    os.environ.setdefault("DCC_MCP_GATEWAY_PORT", "9765")


def _load_dcc_mcp_maya() -> None:
    """Run the fixed captured bootstrap after Maya's startup queue drains."""
    try:
        _apply_default_env()
        _setup_module_paths()
        from dcc_mcp_maya.install import bootstrap_user_setup

        bootstrap_user_setup(defer=False)
    except Exception as exc:
        logger.warning("dcc-mcp-maya auto-load failed: %s", exc)


try:
    import maya.cmds as cmds

    cmds.evalDeferred(_load_dcc_mcp_maya, lowestPriority=True)
except ImportError:
    pass
