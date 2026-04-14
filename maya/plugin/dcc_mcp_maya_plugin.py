"""dcc_mcp_maya_plugin — Maya plugin entry point.

Loads the MCP Streamable HTTP server inside Maya.

**Plugin file naming**: This file is intentionally named ``dcc_mcp_maya_plugin.py``
(not ``dcc_mcp_maya.py``) to avoid a Python namespace collision.  Maya adds the
``plug-ins/`` directory to ``sys.path``, so a file named ``dcc_mcp_maya.py``
would shadow the ``dcc_mcp_maya`` Python package, breaking all imports inside
the plugin itself.

Installation
------------
Copy this file (or create a symlink) into a directory on ``MAYA_PLUG_IN_PATH``.
Load it via **Window > Settings/Preferences > Plug-in Manager**.

Alternatively, add to ``userSetup.py``::

    import maya.cmds as cmds
    cmds.loadPlugin("dcc_mcp_maya_plugin")

Standalone / batch mode
-----------------------
The plugin is fully usable in ``mayapy`` / Maya standalone.  Menu creation is
skipped automatically when ``MayaWindow`` is not available (i.e. non-interactive
sessions).

Configuration
-------------
Environment variables (optional, read at plugin load time):

``DCC_MCP_MAYA_PORT``
    TCP port for the MCP HTTP server.  Default: ``8765``.

``DCC_MCP_MAYA_SERVER_NAME``
    Name advertised in the MCP ``initialize`` response.  Default: ``"maya-mcp"``.

``DCC_MCP_GATEWAY_PORT``
    Gateway competition port.  ``0`` (default) disables gateway participation.
    Set to ``9765`` to join the multi-DCC auto-gateway.

``DCC_MCP_REGISTRY_DIR``
    Directory for the shared ``FileRegistry`` JSON.  Defaults to OS temp dir.
"""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging
import os
import sys
from pathlib import Path

import maya.api.OpenMaya as om  # Python API 2.0 — required for MFnPlugin on Maya 2022-2025
import maya.cmds as cmds

logger = logging.getLogger(__name__)

VENDOR = "dcc-mcp"


# ── ensure dcc_mcp_maya package is importable ────────────────────────────────


def _ensure_package_importable() -> None:
    """Add the module's python/ directory to sys.path if needed.

    Maya GUI mode processes ``PYTHONPATH+:=...`` directives from ``.mod`` files
    automatically, but **Maya standalone / batch mode does not**.  This helper
    ensures the Python package bundled inside the ``.mod`` module directory is
    always importable regardless of how Maya was started.

    It resolves the ``python/`` (or ``python37/`` for Maya 2022) directory
    relative to the ``.mod`` file location and inserts it at the front of
    ``sys.path`` if the ``dcc_mcp_maya`` package cannot already be imported.
    """
    try:
        import dcc_mcp_maya  # noqa: F401 — already importable, nothing to do

        return
    except ImportError:
        pass

    # Resolve the .mod module root: this script lives in <module_root>/plug-ins/
    plugin_dir = Path(__file__).resolve().parent
    module_root = plugin_dir.parent  # <module_root>/

    # Determine which python/ subdir to use based on Maya version
    maya_version = cmds.about(version=True)
    # e.g. "2025", "2024.1" — extract the major version
    try:
        major = int(str(maya_version).split(".")[0])
    except (ValueError, IndexError):
        major = 2025  # safe default

    # Maya 2022 uses Python 3.7 (python37/), later versions use python/
    python_dir = module_root / "python37" if major == 2022 else module_root / "python"
    if not python_dir.is_dir():
        python_dir = module_root / "python"  # fallback

    python_str = str(python_dir)
    if python_str not in sys.path:
        sys.path.insert(0, python_str)
        logger.debug("Added %s to sys.path for dcc_mcp_maya package discovery", python_str)


_ensure_package_importable()


def _get_version() -> str:
    """Read version from the installed package, with static fallback."""
    try:
        from dcc_mcp_maya.__version__ import __version__  # noqa: PLC0415

        return __version__
    except Exception:
        return "0.0.0"


VERSION = _get_version()

# ── module-level server handle ────────────────────────────────────────────────
_handle = None
_menu_name = "DccMcpMenu"

# ── standalone detection ──────────────────────────────────────────────────────


def _is_interactive() -> bool:
    """Return True when Maya is running in interactive (GUI) mode."""
    try:
        return bool(cmds.about(batch=True) is False or not cmds.about(batch=True))
    except Exception:
        return False


# ── plugin API version declaration ──────────────────────────────────────────


def maya_useNewAPI() -> None:
    """Declare Python API 2.0 to Maya.

    When this function is present Maya passes ``MObject`` wrappers from
    API 2.0 (``maya.api.OpenMaya``) to ``initializePlugin`` and
    ``uninitializePlugin`` instead of API 1.0 objects.  Without this
    declaration the two APIs cannot be mixed and ``MFnPlugin`` construction
    may raise ``AttributeError`` in standalone / batch mode.

    References: Autodesk Maya Python API 2.0 documentation.
    """


# ── plugin init ───────────────────────────────────────────────────────────────


def initializePlugin(plugin):
    """Called by Maya when the plugin is loaded."""
    om.MFnPlugin(plugin, VENDOR, VERSION)
    try:
        if _is_interactive():
            _add_menu()
        _start()
        logger.info("dcc-mcp-maya plugin v%s loaded — %s", VERSION, _server_url())
    except Exception as exc:
        logger.error("dcc-mcp-maya plugin failed to initialize: %s", exc)
        raise RuntimeError(f"dcc-mcp-maya init failed: {exc}") from exc


def uninitializePlugin(plugin):
    """Called by Maya when the plugin is unloaded."""
    om.MFnPlugin(plugin)
    try:
        _stop()
        if _is_interactive():
            _remove_menu()
        logger.info("dcc-mcp-maya plugin unloaded")
    except Exception as exc:
        logger.warning("dcc-mcp-maya cleanup error: %s", exc)


# ── server helpers ────────────────────────────────────────────────────────────


def _start() -> None:
    global _handle
    try:
        import dcc_mcp_maya  # noqa: PLC0415

        port = int(os.environ.get("DCC_MCP_MAYA_PORT", "8765"))
        server_name = os.environ.get("DCC_MCP_MAYA_SERVER_NAME", "maya-mcp")
        # Gateway support: read env vars; explicit 0 disables gateway
        gateway_port_str = os.environ.get("DCC_MCP_GATEWAY_PORT", "0")
        gateway_port = int(gateway_port_str) if gateway_port_str.isdigit() else 0
        registry_dir = os.environ.get("DCC_MCP_REGISTRY_DIR") or None
        # Detect Maya version for registry metadata
        try:
            dcc_version = str(cmds.about(version=True))
        except Exception:
            dcc_version = None

        _handle = dcc_mcp_maya.start_server(
            port=port,
            server_name=server_name,
            gateway_port=gateway_port if gateway_port > 0 else None,
            registry_dir=registry_dir,
            dcc_version=dcc_version,
        )
        if gateway_port > 0:
            import dcc_mcp_maya as _pkg  # noqa: PLC0415

            gw = _pkg._server_instance  # noqa: SLF001
            if gw and getattr(gw, "is_gateway", False):
                logger.info("MCP server started at %s [GATEWAY]", _handle.mcp_url())
            else:
                logger.info("MCP server started at %s [instance, gateway=%d]", _handle.mcp_url(), gateway_port)
        else:
            logger.info("MCP server started at %s", _handle.mcp_url())
    except Exception as exc:
        logger.error("Failed to start MCP server: %s", exc)
        raise


def _stop() -> None:
    global _handle
    try:
        import dcc_mcp_maya  # noqa: PLC0415

        dcc_mcp_maya.stop_server()
        _handle = None
    except Exception as exc:
        logger.warning("Failed to stop MCP server: %s", exc)


def _server_url() -> str:
    if _handle is not None:
        try:
            return _handle.mcp_url()
        except Exception:
            pass
    return "<not running>"


# ── menu ─────────────────────────────────────────────────────────────────────


def _add_menu() -> None:
    try:
        if cmds.menu(_menu_name, exists=True):
            cmds.deleteUI(_menu_name)
        cmds.menu(_menu_name, label="DCC MCP", parent="MayaWindow", tearOff=False)
        cmds.menuItem(label="Show MCP URL", command=lambda *_: _show_url())
        cmds.menuItem(label="Restart MCP Server", command=lambda *_: _restart())
        cmds.menuItem(label="Stop MCP Server", command=lambda *_: _stop())
        cmds.menuItem(divider=True)
        cmds.menuItem(label="Open MCP in Browser", command=lambda *_: _open_browser())
    except Exception as exc:
        logger.warning("Could not add DCC MCP menu: %s", exc)


def _remove_menu() -> None:
    try:
        if cmds.menu(_menu_name, exists=True):
            cmds.deleteUI(_menu_name)
    except Exception:
        pass


def _show_url() -> None:
    url = _server_url()
    cmds.confirmDialog(title="MCP Server URL", message=f"Connect your MCP host to:\n\n{url}", button=["OK"])


def _restart() -> None:
    _stop()
    _start()
    cmds.inViewMessage(amg=f"MCP server restarted at <b>{_server_url()}</b>", pos="topCenter", fade=True)


def _open_browser() -> None:
    url = _server_url()
    if url and url != "<not running>":
        import webbrowser  # noqa: PLC0415

        webbrowser.open(url)
    else:
        cmds.warning("MCP server is not running.")
