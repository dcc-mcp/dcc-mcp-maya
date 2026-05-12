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

Gateway mode (default ON)
-------------------------
By default the plugin joins the auto-gateway on port ``9765``.  The first Maya
instance to start becomes the **gateway**; subsequent instances register as plain
DCC instances.  Both expose their own full MCP tool set.

Connect your MCP client (Claude Desktop, etc.) to the **single gateway endpoint**::

    http://127.0.0.1:9765/mcp

The gateway exposes three discovery meta-tools:
  - ``list_dcc_instances`` — show all running Maya instances
  - ``connect_to_dcc``     — get the direct URL for a specific instance
  - ``get_dcc_instance``   — query a specific instance by id or scene

To **disable** the gateway: set ``DCC_MCP_GATEWAY_PORT=0`` before starting Maya.

Configuration
-------------
``DCC_MCP_MAYA_PORT``
    TCP port for this instance's MCP HTTP server.  Default ``0`` (OS-assigned).
    Using ``0`` is recommended when running multiple Maya instances.

``DCC_MCP_MAYA_SERVER_NAME``
    Name advertised in the MCP ``initialize`` response.  Default: ``"maya-mcp"``.

``DCC_MCP_GATEWAY_PORT``
    Gateway competition port.  Default ``9765``.  Set to ``0`` to disable.

``DCC_MCP_REGISTRY_DIR``
    Directory for the shared ``FileRegistry`` JSON.  Defaults to OS temp dir.

``DCC_MCP_MAYA_WINDOW_TITLE``
    Optional substring of the main Maya window title, passed to the MCP server
    as ``dcc_window_title`` for instance-bound diagnostics and screenshot routing
    (``dcc-mcp-core`` 0.14+).  Usually unnecessary; same-process PID resolution
    is the default.

``DCC_MCP_PYTHON_EXECUTABLE``
    Python interpreter for skill worker subprocesses.  Auto-set to
    ``sys.executable`` (i.e. ``mayapy``) at plugin load time.

``DCC_MCP_PYTHON_INIT_SNIPPET``
    One-liner executed by each skill worker before running any tool script.
    Auto-set to ``import maya.standalone; maya.standalone.initialize(name='python')``.
"""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging
import os
import sys
import threading
from pathlib import Path

import maya.api.OpenMaya as om  # Python API 2.0 — required for MFnPlugin on Maya 2020+
import maya.cmds as cmds

logger = logging.getLogger(__name__)

VENDOR = "dcc-mcp"

# Default gateway port — same as dcc-mcp-server binary default
_DEFAULT_GATEWAY_PORT = 9765


# ── ensure dcc_mcp_maya package is importable ────────────────────────────────


def _ensure_package_importable() -> None:
    """Add the module's python/ directory to sys.path if needed."""
    try:
        import dcc_mcp_maya  # noqa: F401 — already importable, nothing to do

        return
    except ImportError:
        pass

    plugin_dir = Path(__file__).resolve().parent
    module_root = plugin_dir.parent

    python_dir = module_root / ("python37" if sys.version_info[:2] == (3, 7) else "python")
    if not python_dir.is_dir():
        python_dir = module_root / "python"
    python_str = str(python_dir)
    if python_dir.is_dir() and python_str not in sys.path:
        sys.path.insert(0, python_str)
        logger.debug("Added %s to sys.path for dcc_mcp_maya package discovery", python_str)


_ensure_package_importable()


def _get_version() -> str:
    try:
        from dcc_mcp_maya.__version__ import __version__  # noqa: PLC0415

        return __version__
    except Exception:
        return "0.0.0"


VERSION = _get_version()

# ── module-level state ────────────────────────────────────────────────────────
_handle = None
_host = None
_host_dispatcher = None
_menu_name = "DccMcpMenu"
_restart_lock = threading.Lock()  # prevent overlapping restart calls
_shutdown_coordinator = None  # Issue #186 — safety-net composition root
_startup_thread = None


# ── standalone detection ──────────────────────────────────────────────────────


def _is_interactive() -> bool:
    """Return True when Maya is running in interactive (GUI) mode."""
    try:
        return not cmds.about(batch=True)
    except Exception:
        return False


# ── plugin API version declaration ──────────────────────────────────────────


def maya_useNewAPI() -> None:
    """Declare Python API 2.0 to Maya."""


# ── plugin init ───────────────────────────────────────────────────────────────


def initializePlugin(plugin):
    """Called by Maya when the plugin is loaded."""
    om.MFnPlugin(plugin, VENDOR, VERSION)
    try:
        if _is_interactive():
            _add_menu()
        if _is_interactive():
            _start_async()
        else:
            _start()
    except Exception as exc:
        logger.error("dcc-mcp-maya plugin failed to initialize: %s", exc)
        raise RuntimeError(f"dcc-mcp-maya init failed: {exc}") from exc


def uninitializePlugin(plugin):
    """Called by Maya when the plugin is unloaded.

    Issue #126 — every cleanup step runs even when an earlier one raises so
    the FileRegistry entry is always released.  ``_stop_blocking()`` is
    invoked from a ``finally`` block so a menu-removal failure (e.g. partial
    UI shutdown) cannot leak the running server.

    Issue #186 — the shutdown safety nets installed at plugin load are
    uninstalled in the same ``finally`` path (before ``_stop_blocking``)
    so they do not fire a second time while plugin cleanup is already in
    flight.
    """
    om.MFnPlugin(plugin)
    try:
        if _is_interactive():
            try:
                _remove_menu()
            except Exception as exc:  # noqa: BLE001
                logger.warning("dcc-mcp-maya menu removal error: %s", exc)
    finally:
        try:
            _uninstall_shutdown_safety()
        except Exception as exc:  # noqa: BLE001
            logger.warning("dcc-mcp-maya shutdown safety teardown error: %s", exc)
        try:
            _stop_blocking()
        except Exception as exc:  # noqa: BLE001
            logger.warning("dcc-mcp-maya server stop error: %s", exc)
        logger.info("dcc-mcp-maya plugin unloaded")


# ── server helpers ────────────────────────────────────────────────────────────


def _resolve_config():
    """Read all config from env vars and return as a dict."""
    port = int(os.environ.get("DCC_MCP_MAYA_PORT", "0"))
    server_name = os.environ.get("DCC_MCP_MAYA_SERVER_NAME", "maya-mcp")
    gateway_port_str = os.environ.get("DCC_MCP_GATEWAY_PORT", str(_DEFAULT_GATEWAY_PORT))
    try:
        gateway_port = int(gateway_port_str)
    except ValueError:
        gateway_port = _DEFAULT_GATEWAY_PORT
    registry_dir = os.environ.get("DCC_MCP_REGISTRY_DIR") or None
    try:
        dcc_version = str(cmds.about(version=True))
    except Exception:
        dcc_version = None
    out = {
        "port": port,
        "server_name": server_name,
        "gateway_port": gateway_port if gateway_port > 0 else None,
        "registry_dir": registry_dir,
        "dcc_version": dcc_version,
    }
    # Optional: helps WindowFinder / diagnostics__screenshot when PIDs are ambiguous
    wtitle = os.environ.get("DCC_MCP_MAYA_WINDOW_TITLE", "").strip()
    if wtitle:
        out["dcc_window_title"] = wtitle
    return out


def _export_worker_env() -> None:
    """Export env vars for the subprocess fallback path.

    ``MayaMcpServer.register_builtin_actions`` wires an in-process executor
    (issue #108) so skills normally run inside the live Maya interpreter.
    This function is still called as a safety net: if the in-process path is
    unavailable (dcc-mcp-core < 0.14) the core skill launcher falls back to
    spawning a subprocess and these env vars ensure it uses the correct
    ``mayapy`` and initialises Maya standalone.

    ``DCC_MCP_PYTHON_EXECUTABLE``
        Points at ``mayapy`` so the subprocess uses the same interpreter.

    ``DCC_MCP_PYTHON_INIT_SNIPPET``
        Initialises Maya standalone in the worker process.

    Uses ``setdefault`` so advanced users can still override.
    See: https://github.com/loonghao/dcc-mcp-maya/issues/63, #108
    """
    os.environ.setdefault("DCC_MCP_PYTHON_EXECUTABLE", sys.executable)
    os.environ.setdefault(
        "DCC_MCP_PYTHON_INIT_SNIPPET",
        "import maya.standalone; maya.standalone.initialize(name='python')",
    )
    # Issue #125 — auto-correct DCC_MCP_PYTHON_EXECUTABLE if it points at maya.exe
    # (GUI) instead of mayapy.exe (headless).  Idempotent; no-op when the env
    # var already points at a Python interpreter or when core < 0.14.17.
    try:
        from dcc_mcp_maya._pyexec import auto_correct as _auto_correct_pyexec  # noqa: PLC0415

        _auto_correct_pyexec()
    except Exception as exc:  # noqa: BLE001 — never block plugin load
        logger.debug("DCC_MCP_PYTHON_EXECUTABLE auto-correct skipped: %s", exc)
    logger.debug(
        "Subprocess fallback env set: DCC_MCP_PYTHON_EXECUTABLE=%s",
        os.environ["DCC_MCP_PYTHON_EXECUTABLE"],
    )


def _start() -> None:
    """Start the MCP server (called from Maya main thread)."""
    global _handle, _host, _host_dispatcher
    try:
        from dcc_mcp_core.host import BlockingDispatcher, QueueDispatcher  # noqa: PLC0415

        import dcc_mcp_maya  # noqa: PLC0415

        _export_worker_env()
        # Issue #148 — defuse the modal commandPort security warning that
        # would otherwise freeze Maya's main thread when a stray client
        # (or the gateway probe) connects to the legacy commandPort.
        try:
            from dcc_mcp_maya._commandport import suppress_security_warnings  # noqa: PLC0415

            suppress_security_warnings()
        except Exception as exc:  # noqa: BLE001 — never block plugin load
            logger.debug("commandPort warning suppression skipped: %s", exc)
        cfg = _resolve_config()
        _host_dispatcher = BlockingDispatcher() if cmds.about(batch=True) else QueueDispatcher()
        _host = dcc_mcp_maya.MayaHost(_host_dispatcher)
        _handle = dcc_mcp_maya.start_server(host_dispatcher=_host_dispatcher, **cfg)
        _host.start()
        _post_start(cfg)
    except Exception as exc:
        logger.error("Failed to start MCP server: %s", exc)
        raise


def _start_async() -> None:
    """Start the MCP server off Maya's UI thread, then attach the idle pump."""
    global _handle, _host, _host_dispatcher, _startup_thread
    try:
        from dcc_mcp_core.host import QueueDispatcher  # noqa: PLC0415

        import dcc_mcp_maya  # noqa: PLC0415

        _export_worker_env()
        try:
            from dcc_mcp_maya._commandport import suppress_security_warnings  # noqa: PLC0415

            suppress_security_warnings()
        except Exception as exc:  # noqa: BLE001
            logger.debug("commandPort warning suppression skipped: %s", exc)
        cfg = _resolve_config()
        _host_dispatcher = QueueDispatcher()
        _host = dcc_mcp_maya.MayaHost(_host_dispatcher)

        def _finish_on_main() -> None:
            try:
                if _host is not None:
                    _host.start()
                _post_start(cfg)
            except Exception as exc:  # noqa: BLE001
                logger.error("dcc-mcp-maya async startup finalization failed: %s", exc)

        def _worker() -> None:
            global _handle
            try:
                _handle = dcc_mcp_maya.start_server(host_dispatcher=_host_dispatcher, **cfg)
                cmds.evalDeferred(_finish_on_main, lowestPriority=True)
            except Exception as exc:  # noqa: BLE001
                logger.error("Failed to start MCP server asynchronously: %s", exc)

        _startup_thread = threading.Thread(target=_worker, name="dcc-mcp-maya-startup", daemon=True)
        _startup_thread.start()
    except Exception as exc:
        logger.error("Failed to schedule async MCP server startup: %s", exc)
        raise


def _post_start(cfg: dict) -> None:
    _print_startup_info(cfg)
    _install_shutdown_safety()
    try:
        from dcc_mcp_maya._log_hygiene import prune_maya_logs  # noqa: PLC0415

        prune_maya_logs()
    except Exception as exc:  # noqa: BLE001
        logger.debug("log pruning skipped: %s", exc)
    try:
        from dcc_mcp_maya._stale_cleanup import warn_if_too_many_stale  # noqa: PLC0415

        warn_if_too_many_stale(
            registry_dir=os.environ.get("DCC_MCP_REGISTRY_DIR") or None,
        )
    except Exception as exc:  # noqa: BLE001
        logger.debug("stale-instance scan skipped: %s", exc)


def _print_startup_info(cfg: dict) -> None:
    """Print startup info to Maya console and script editor."""
    import dcc_mcp_maya.server as _srv_mod  # noqa: PLC0415

    instance_url = _handle.mcp_url() if _handle else "<not running>"
    gateway_port = cfg.get("gateway_port") or 0
    dcc_version = cfg.get("dcc_version") or "unknown"

    srv = _srv_mod._server_instance  # noqa: SLF001
    is_gw = bool(srv and getattr(srv, "is_gateway", False))

    # ── banner ────────────────────────────────────────────────────────────────
    border = "=" * 60
    lines = [
        border,
        f"  dcc-mcp-maya v{VERSION}  |  Maya {dcc_version}",
        border,
        f"  Instance URL : {instance_url}",
    ]

    if gateway_port > 0:
        gw_url = f"http://127.0.0.1:{gateway_port}"
        if is_gw:
            lines.append(f"  Gateway URL  : {gw_url}  [THIS INSTANCE IS GATEWAY]")
            lines.append(f"  Connect MCP client to: {gw_url}/mcp")
        else:
            lines.append(f"  Gateway URL  : {gw_url}  [registered as instance]")
            lines.append(f"  Connect MCP client to: {gw_url}/mcp  (via gateway)")
        lines.append("  Gateway tools: list_dcc_instances / connect_to_dcc")
    else:
        lines.append(f"  Connect MCP client to: {instance_url}")
        lines.append("  (Gateway disabled — set DCC_MCP_GATEWAY_PORT=9765 to enable)")

    lines.append(border)

    banner = "\n".join(lines)

    # Print to Maya script editor / output window
    print(banner)  # noqa: T201 — intentional console output

    # Also show in Maya viewport HUD (interactive mode only)
    if _is_interactive() and _handle:
        try:
            if is_gw:
                hud_msg = f"DCC MCP <b>[GATEWAY]</b> {gw_url}/mcp"
            elif gateway_port > 0:
                hud_msg = f"DCC MCP <b>[instance]</b> → gateway {gw_url}/mcp"
            else:
                hud_msg = f"DCC MCP ready: {instance_url}"
            cmds.inViewMessage(amg=hud_msg, pos="topCenter", fade=True, fadeStayTime=4000)
        except Exception:
            pass  # viewport HUD is cosmetic, never block startup


def _stop_blocking() -> None:
    """Stop the server, blocking until fully shut down.

    Safe to call from any thread.  Uses the standard stop_server() path
    which calls handle.shutdown() (blocking).  Only used during plugin
    unload (``uninitializePlugin``), where blocking is acceptable.
    """
    global _handle, _host, _host_dispatcher
    try:
        if _host is not None:
            _host.stop()
            _host = None
            _host_dispatcher = None
        import dcc_mcp_maya  # noqa: PLC0415

        dcc_mcp_maya.stop_server()
        _handle = None
    except Exception as exc:
        logger.warning("Failed to stop MCP server: %s", exc)


# ── shutdown safety nets (issue #186) ─────────────────────────────────────────


def _resolve_instance_id() -> str:
    """Return the Maya MCP instance id for the active server, or ``"unknown"``.

    Used to tag the crash-resilient process sentinel (issue #186) so
    sweepers can cross-reference a FileRegistry row against its
    sentinel.  Robust to every degraded state — missing server,
    Python-3.7 fallback path, server not yet registered — because the
    tag is cosmetic; the sentinel's filesystem presence is what
    actually matters.
    """
    try:
        import dcc_mcp_maya  # noqa: PLC0415

        server = getattr(dcc_mcp_maya.server, "_server_instance", None)
        if server is not None:
            instance_id = getattr(server, "instance_id", None)
            if instance_id:
                return str(instance_id)
    except Exception as exc:  # noqa: BLE001
        logger.debug("instance id lookup failed: %s", exc)
    return "unknown"


def _install_shutdown_safety() -> None:
    """Wire the ``kMayaExiting`` / ``atexit`` / sentinel / __del__ safety nets.

    Called from :func:`initializePlugin` immediately after ``_start()``
    so the coordinator can tag the process sentinel with the freshly
    allocated instance id.  Never raises — a failure here degrades to
    "only ``uninitializePlugin`` can clean up", which is the pre-#186
    behaviour.
    """
    global _shutdown_coordinator
    try:
        from dcc_mcp_maya._shutdown_safety import ShutdownCoordinator  # noqa: PLC0415
    except Exception as exc:  # noqa: BLE001
        logger.debug("shutdown safety module unavailable: %s", exc)
        return
    try:
        coordinator = ShutdownCoordinator()
        coordinator.install(
            stop_callback=_stop_blocking,
            instance_id=_resolve_instance_id(),
            registry_dir=os.environ.get("DCC_MCP_REGISTRY_DIR") or None,
        )
        _shutdown_coordinator = coordinator
        logger.debug("shutdown safety nets installed (issue #186)")
    except Exception as exc:  # noqa: BLE001
        logger.warning("shutdown safety install failed: %s", exc)


def _uninstall_shutdown_safety() -> None:
    """Tear down the shutdown safety nets installed by :func:`_install_shutdown_safety`.

    Idempotent — safe when install failed or was never called.
    """
    global _shutdown_coordinator
    coord = _shutdown_coordinator
    _shutdown_coordinator = None
    if coord is None:
        return
    try:
        coord.uninstall()
    except Exception as exc:  # noqa: BLE001
        logger.debug("shutdown safety uninstall failed: %s", exc)


def _stop_async() -> None:
    """Signal shutdown without blocking the Maya main thread.

    Sends a non-blocking shutdown signal, then waits in a background
    thread.  Used by the Restart menu item to avoid freezing Maya.
    """
    global _handle, _host, _host_dispatcher
    try:
        import dcc_mcp_maya.server as _srv_mod  # noqa: PLC0415

        # Signal shutdown (non-blocking — returns immediately)
        srv = _srv_mod._server_instance  # noqa: SLF001
        if srv and srv._handle:
            srv._handle.signal_shutdown()

        if _host is not None:
            _host.stop()
            _host = None
            _host_dispatcher = None

        # Deregister singleton so start_server() creates a fresh instance
        _srv_mod._server_instance = None  # noqa: SLF001
        _handle = None
    except Exception as exc:
        logger.warning("Failed to signal MCP server shutdown: %s", exc)


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
        cmds.menuItem(label="Restart MCP Server", command=lambda *_: _restart_deferred())
        cmds.menuItem(label="Stop MCP Server", command=lambda *_: _stop_blocking())
        cmds.menuItem(divider=True)
        cmds.menuItem(label="Enable/Disable Hot Reload", command=lambda *_: _toggle_hot_reload())
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
    import dcc_mcp_maya.server as _srv_mod  # noqa: PLC0415

    srv = _srv_mod._server_instance  # noqa: SLF001
    instance_url = _server_url()
    gateway_port = int(os.environ.get("DCC_MCP_GATEWAY_PORT", str(_DEFAULT_GATEWAY_PORT)))
    is_gw = bool(srv and getattr(srv, "is_gateway", False))

    if gateway_port > 0:
        gw_url = f"http://127.0.0.1:{gateway_port}/mcp"
        if is_gw:
            msg = f"Gateway (this instance):\n  {gw_url}\n\nInstance URL:\n  {instance_url}"
        else:
            msg = f"Gateway:\n  {gw_url}\n\nThis instance:\n  {instance_url}"
    else:
        msg = f"MCP Server URL:\n  {instance_url}"

    cmds.confirmDialog(title="DCC MCP — Server URLs", message=msg, button=["OK"])


def _restart_deferred() -> None:
    """Restart the MCP server without blocking the Maya main thread.

    Pattern:
      1. Signal shutdown (non-blocking, returns immediately).
      2. Spawn a background thread that waits ~0.5 s for the Rust runtime
         to drain, then reschedules _start() back on the Maya main thread
         via ``maya.utils.executeDeferred``.
    """
    if not _restart_lock.acquire(blocking=False):
        cmds.warning("DCC MCP: restart already in progress, please wait.")
        return

    cmds.inViewMessage(amg="DCC MCP: restarting…", pos="topCenter", fade=True)
    _stop_async()

    def _bg_restart():
        import time

        time.sleep(0.6)  # let the Rust runtime finish shutting down

        try:
            import maya.utils  # noqa: PLC0415

            maya.utils.executeDeferred(_main_thread_start)
        except Exception as exc:
            logger.error("DCC MCP: background restart failed: %s", exc)
        finally:
            _restart_lock.release()

    def _main_thread_start():
        try:
            _start()
        except Exception as exc:
            logger.error("DCC MCP: restart _start() failed: %s", exc)

    threading.Thread(target=_bg_restart, daemon=True, name="dcc-mcp-restart").start()


def _open_browser() -> None:
    url = _server_url()
    if url and url != "<not running>":
        import webbrowser  # noqa: PLC0415

        webbrowser.open(url)
    else:
        cmds.warning("MCP server is not running.")


def _toggle_hot_reload() -> None:
    """Toggle hot-reload on/off for the MCP server."""
    import dcc_mcp_maya.server as _srv_mod  # noqa: PLC0415

    srv = _srv_mod._server_instance  # noqa: SLF001
    if srv is None:
        cmds.warning("MCP server is not running.")
        return

    try:
        if srv.is_hot_reload_enabled:
            srv.disable_hot_reload()
            cmds.inViewMessage(amg="DCC MCP: hot-reload <b>disabled</b>", pos="topCenter", fade=True, fadeStayTime=2000)
            print("Hot-reload disabled")  # noqa: T201
        else:
            if srv.enable_hot_reload():
                stats = srv.hot_reload_stats
                msg = f"DCC MCP: hot-reload <b>enabled</b> ({len(stats['watched_paths'])} paths)"
                cmds.inViewMessage(amg=msg, pos="topCenter", fade=True, fadeStayTime=2000)
                print(f"Hot-reload enabled: monitoring {len(stats['watched_paths'])} paths")  # noqa: T201
            else:
                cmds.warning("Failed to enable hot-reload")
    except Exception as exc:
        logger.error("Hot-reload toggle error: %s", exc)
        cmds.warning(f"Error toggling hot-reload: {exc}")
