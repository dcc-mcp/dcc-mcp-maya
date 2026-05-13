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

The gateway exposes a bounded dynamic surface (``search_tools`` / ``describe_tool`` /
``call_tool``) and MCP ``resources/read`` on ``gateway://instances`` for instance
discovery (see ``gateway://docs/agent-workflows``). Legacy ``list_dcc_instances`` /
``connect_to_dcc`` meta-tools are no longer advertised on current gateways.

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


def _plugin_dir() -> Path:
    """Directory containing this plugin file (``plug-ins/``).

    Maya sometimes loads ``.py`` plug-ins in a context where ``__file__`` is
    not injected; fall back to the code object filename (same approach as
    ``inspect.getfile(inspect.currentframe())`` but without importing inspect).
    """
    try:
        return Path(__file__).resolve().parent
    except NameError:
        # Frame 0 is this function; co_filename is the path to this source file.
        return Path(sys._getframe(0).f_code.co_filename).resolve().parent


def _ensure_package_importable() -> None:
    """Prefer the sibling ``python/`` (or ``python37/``) tree next to this plugin.

    Maya may already have a different ``dcc_mcp_core`` / ``dcc_mcp_maya`` on
    ``sys.path`` (site-packages, PYTHONPATH).  A mismatched pair leaves
    ``dcc_mcp_core`` half-initialised when ``from dcc_mcp_core import _core``
    races with lazy submodules — the classic "partially initialized module"
    error.  We therefore pin the module-root ``python*`` directory to the
    *front* of ``sys.path`` and drop stale ``sys.modules`` entries when their
    files are not under that tree or when the first import fails.
    """
    plugin_dir = _plugin_dir()
    module_root = plugin_dir.parent
    python_dir = module_root / ("python37" if sys.version_info[:2] == (3, 7) else "python")
    if not python_dir.is_dir():
        python_dir = module_root / "python"
    if not python_dir.is_dir():
        return

    python_str = str(python_dir.resolve())

    def _prepend_python_path() -> None:
        while python_str in sys.path:
            sys.path.remove(python_str)
        sys.path.insert(0, python_str)
        logger.debug("Pinned %s to front of sys.path for dcc-mcp-maya imports", python_str)

    def _purge_dcc_modules() -> None:
        keys = [
            k
            for k in list(sys.modules)
            if k == "dcc_mcp_core"
            or k.startswith("dcc_mcp_core.")
            or k == "dcc_mcp_maya"
            or k.startswith("dcc_mcp_maya.")
        ]
        for k in keys:
            del sys.modules[k]

    def _module_tree_wrong_origin(name: str) -> bool:
        mod = sys.modules.get(name)
        if mod is None:
            return False
        roots = []
        mod_file = getattr(mod, "__file__", None)
        if mod_file:
            roots.append(os.path.dirname(os.path.realpath(mod_file)))
        for entry in getattr(mod, "__path__", None) or ():
            roots.append(os.path.realpath(entry))
        if not roots:
            return False
        want = os.path.realpath(python_str)
        return not any(r == want or r.startswith(want + os.sep) for r in roots)

    _prepend_python_path()

    if _module_tree_wrong_origin("dcc_mcp_maya") or _module_tree_wrong_origin("dcc_mcp_core"):
        logger.warning(
            "Reloading dcc_mcp_* from %s (cached modules were not from this module root)",
            python_str,
        )
        _purge_dcc_modules()
        _prepend_python_path()

    try:
        import dcc_mcp_maya  # noqa: F401
    except ImportError:
        _purge_dcc_modules()
        _prepend_python_path()
        import dcc_mcp_maya  # noqa: F401


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
            _start()
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
    """Defer MCP server startup until Maya's main-thread boot is complete.

    Design rationale
    ----------------
    Three previous revisions tried to keep ``initializePlugin`` non-blocking
    by spawning a worker thread for ``start_server(...)`` and then handing
    finalisation back to the UI thread. Every variant had a real-world
    failure mode in interactive Maya:

    1. ``cmds.evalDeferred(_finish_on_main, lowestPriority=True)`` from the
       worker thread crashed with "必须为标志'lowestPriority'传递一个布尔
       参数" — ``cmds.*`` is not thread-safe; kwargs are marshalled through
       the MEL command engine on the wrong thread.

    2. ``maya.utils.executeDeferred(_finish_on_main)`` from the worker
       thread was thread-safe in theory (it routes through
       ``executeInMainThreadWithResult`` to add the call to the deferred
       queue) but **deadlocked** Maya in 2022/2023 builds: that channel is
       gated on a state flag flipped only after plugin-init completes, so
       the worker (holding the GIL while waiting) and the main thread
       (inside ``initializePlugin``, waiting on the worker via the GIL)
       form a cycle that pins Maya.

    3. ``cmds.scriptJob(idleEvent=poll, protected=True)`` + a
       ``threading.Event`` polled from the worker still raced against
       Maya's plugin-init re-entrancy guards in some builds — the same
       ``executeInMainThread`` channel is needed to register the scriptJob
       safely from non-main threads, and Maya's idle-event dispatch can
       freeze briefly during the late phases of boot.

    The current design (per user request 2026-05-13) is the **simplest**
    path that works everywhere: stay on the main thread, wait for Maya to
    finish booting, then run the synchronous startup path in-place.

    * ``initializePlugin`` is invoked on Maya's main thread.
    * ``cmds.evalDeferred(_start, lowestPriority=True)`` queues ``_start``
      at the **back** of Maya's deferred queue, *behind* every other
      pending deferred task: ``userSetup.py`` follow-ups, autoload scene,
      other plugins' init code, etc.
    * When ``_start`` finally fires, Maya's main thread is fully idle and
      the UI is responsive. ``start_server(...)`` and ``MayaHost.start()``
      run synchronously on the main thread — no cross-thread invoke, no
      worker, no scriptJob polling, no event coordination.
    * ``start_server(...)`` itself spawns the HTTP server / gateway
      election in its own internal worker threads; those don't need to
      coordinate back to the main thread for completion (they are
      independent loops).

    The trade-off: when ``_start`` fires it briefly blocks the Maya UI
    while skill discovery + builtin action registration happen (~10–500
    ms depending on skill count). This pause is invisible to users
    because it lands during the post-boot idle moment when Maya is
    already showing its empty scene; the alternative (an unreliable
    cross-thread hand-off that occasionally pins Maya forever) is far
    worse.
    """
    try:
        cmds.evalDeferred(_start, lowestPriority=True)
    except Exception as exc:
        logger.error("Failed to schedule MCP server startup: %s", exc)
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
        lines.append("  Instance discovery: MCP resources/read uri=gateway://instances")
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


def _stop_host_on_main_thread() -> None:
    """Stop the Maya host idle tick (``detach_tick`` / ``scriptJob`` — main thread only)."""
    global _host, _host_dispatcher
    if _host is None:
        return
    try:
        _host.stop()
    except Exception as exc:  # noqa: BLE001
        logger.warning("MCP host stop failed: %s", exc)
    finally:
        _host = None
        _host_dispatcher = None


def _running_mcp_server():
    """Return the live :class:`~dcc_mcp_maya.server.MayaMcpServer` or ``None``.

    Prefer the public module alias, but fall back to the internal holder so
    menu actions still work if those two ever diverge during a bad partial
    shutdown path.
    """
    import dcc_mcp_maya.server as _srv_mod  # noqa: PLC0415

    srv = _srv_mod._server_instance  # noqa: SLF001
    if srv is not None:
        return srv
    holder = getattr(_srv_mod, "_instance_holder", None)
    if holder and holder[0] is not None:
        return holder[0]
    return None


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
        cmds.menuItem(label="OpenAPI Docs", command=lambda *_: _open_openapi_docs())
        cmds.menuItem(label="Admin Panel", command=lambda *_: _open_admin_panel())
        cmds.menuItem(divider=True)
        cmds.menuItem(label="Restart MCP Server", command=lambda *_: _restart_deferred())
        cmds.menuItem(label="Stop MCP Server", command=lambda *_: _stop_blocking())
        cmds.menuItem(divider=True)
        cmds.menuItem(label="Enable/Disable Hot Reload", command=lambda *_: _toggle_hot_reload())
    except Exception as exc:
        logger.warning("Could not add DCC MCP menu: %s", exc)


def _remove_menu() -> None:
    try:
        if cmds.menu(_menu_name, exists=True):
            cmds.deleteUI(_menu_name)
    except Exception:
        pass


def _show_url() -> None:
    srv = _running_mcp_server()
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
    """Restart the MCP server without blocking the Maya UI thread for long.

    ``MayaHost.stop()`` / ``detach_tick`` must run on the Maya main thread.
    ``dcc_mcp_maya.stop_server()`` joins the Rust HTTP stack and may take
    hundreds of milliseconds — that work runs on a daemon thread.  A prior
    implementation only ``signal_shutdown`` + cleared ``_server_instance``
    without clearing ``_instance_holder``; ``start_server()`` then saw the old
    server as still ``is_running`` and returned the stale handle, so Restart
    appeared to do nothing and Hot Reload thought the server was down.
    """
    if not _restart_lock.acquire(blocking=False):
        cmds.warning("DCC MCP: restart already in progress, please wait.")
        return

    cmds.inViewMessage(amg="DCC MCP: restarting…", pos="topCenter", fade=True)

    try:
        _stop_host_on_main_thread()
    except Exception as exc:  # noqa: BLE001
        logger.warning("DCC MCP: restart host phase failed: %s", exc)

    def _main_thread_finish_restart() -> None:
        try:
            _start()
        except Exception as exc:
            logger.error("DCC MCP: restart _start() failed: %s", exc)
        finally:
            _restart_lock.release()

    def _bg_shutdown_then_schedule_start() -> None:
        global _handle
        try:
            import dcc_mcp_maya  # noqa: PLC0415

            dcc_mcp_maya.stop_server()
        except Exception as exc:
            logger.warning("DCC MCP: restart stop_server failed: %s", exc)
        finally:
            _handle = None
        try:
            import maya.utils  # noqa: PLC0415

            maya.utils.executeDeferred(_main_thread_finish_restart)
        except Exception as exc:
            logger.error("DCC MCP: restart executeDeferred failed: %s", exc)
            _restart_lock.release()

    threading.Thread(
        target=_bg_shutdown_then_schedule_start,
        daemon=True,
        name="dcc-mcp-restart",
    ).start()


def _open_browser() -> None:
    url = _server_url()
    if url and url != "<not running>":
        import webbrowser  # noqa: PLC0415

        webbrowser.open(url)
    else:
        cmds.warning("MCP server is not running.")


def _openapi_base_url() -> str:
    """Return base URL for the running server (strip /mcp suffix)."""
    url = _server_url()
    if url and url != "<not running>":
        return url.replace("/mcp", "")
    return ""


def _open_openapi_docs() -> None:
    """Open the DCC service OpenAPI docs (Swagger UI) in the default browser."""
    base = _openapi_base_url()
    if not base:
        cmds.warning("MCP server is not running.")
        return
    import webbrowser  # noqa: PLC0415

    webbrowser.open(base + "/docs")


def _gateway_url() -> str:
    """Return the gateway base URL (from DCC_MCP_GATEWAY_PORT env var)."""
    gateway_port = int(os.environ.get("DCC_MCP_GATEWAY_PORT", str(_DEFAULT_GATEWAY_PORT)))
    if gateway_port <= 0:
        return ""
    return f"http://127.0.0.1:{gateway_port}"


def _open_admin_panel() -> None:
    """Open the gateway admin panel in the default browser."""
    gw = _gateway_url()
    if not gw:
        cmds.warning("Gateway is disabled (DCC_MCP_GATEWAY_PORT=0). Cannot open admin panel.")
        return
    import webbrowser  # noqa: PLC0415

    webbrowser.open(gw + "/admin")


def _toggle_hot_reload() -> None:
    """Toggle hot-reload on/off for the MCP server."""
    srv = _running_mcp_server()
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
