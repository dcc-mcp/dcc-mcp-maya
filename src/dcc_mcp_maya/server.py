"""MayaMcpServer — embedded MCP Streamable HTTP server for Maya.

Composition root after the issue #127 SRP decomposition.  The heavy
lifting lives in private sibling modules so this file stays focused on
wiring:

================  ===========================================================
Module            Responsibility
================  ===========================================================
``_env``          ``DCC_MCP_MAYA_*`` env-var resolution
``_executor``    In-process skill execution + handler registration
``_skill_loader`` Minimal-mode skill loading (constants + loaders)
``_version_probe`` Maya availability + version string detection
``_transport``    ``TransportManager`` wrappers (bind/find/rank)
``_pyexec``       ``DCC_MCP_PYTHON_EXECUTABLE`` auto-correction (#125)
================  ===========================================================

All public surface is preserved 1:1.
"""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging
import os
import threading
from pathlib import Path
from typing import Any, List, Optional

# Import third-party modules
from dcc_mcp_core.factory import create_dcc_server
from dcc_mcp_core.server_base import DccServerBase

# Import local modules
from dcc_mcp_maya import _env, _executor, _skill_loader, _transport, _version_probe
from dcc_mcp_maya.__version__ import __version__

logger = logging.getLogger(__name__)

DEFAULT_SERVER_VERSION = __version__

#: Built-in skills directory shipped with this package.
_BUILTIN_SKILLS_DIR = Path(__file__).resolve().parent / "skills"


class MayaMcpServer(DccServerBase):
    """MCP Streamable HTTP server embedded inside Maya.

    Thin composition root that extends
    :class:`~dcc_mcp_core.server_base.DccServerBase` with Maya-specific
    behaviour:

    * Maya built-in skills directory (``skills/``).
    * Maya version detection via :func:`_version_probe.get_maya_version_string`.
    * Minimal-mode startup — only core skills are loaded; the rest
      remain as ``__skill__`` stubs for progressive activation.
    * In-process skill execution via :mod:`_executor`.
    * Maya-specific :class:`TransportManager` wrappers (delegated to
      :mod:`_transport`).
    * Prometheus ``/metrics`` endpoint (issue #87) and SQLite job
      persistence (issue #89) — env vars resolved by :mod:`_env`.

    Example::

        server = MayaMcpServer(port=8765)
        server.register_builtin_actions()
        handle = server.start()
        print(handle.mcp_url())    # http://127.0.0.1:8765/mcp
        handle.shutdown()
    """

    def __init__(
        self,
        port: int = 8765,
        server_name: str = "maya-mcp",
        server_version: str = DEFAULT_SERVER_VERSION,
        gateway_port: Optional[int] = None,
        registry_dir: Optional[str] = None,
        dcc_version: Optional[str] = None,
        scene: Optional[str] = None,
        enable_gateway_failover: bool = True,
        metrics_enabled: Optional[bool] = None,
        job_storage_path: Optional[str] = None,
        job_recovery: Optional[str] = None,
        dcc_pid: Optional[int] = None,
        dcc_window_title: Optional[str] = None,
        dcc_window_handle: Optional[int] = None,
        enable_workflows: Optional[bool] = None,
    ) -> None:
        super().__init__(
            dcc_name="maya",
            builtin_skills_dir=_BUILTIN_SKILLS_DIR,
            port=port,
            server_name=server_name,
            server_version=server_version,
            gateway_port=gateway_port,
            registry_dir=registry_dir,
            dcc_version=dcc_version,
            scene=scene,
            enable_gateway_failover=enable_gateway_failover,
            dcc_pid=dcc_pid,
            dcc_window_title=dcc_window_title,
            dcc_window_handle=dcc_window_handle,
        )

        # ── Prometheus metrics (issue #87) ──────────────────────────────
        if _env.resolve_metrics_enabled(metrics_enabled):
            self._config.enable_prometheus = True
            logger.info("[%s] Prometheus /metrics endpoint enabled", "maya")

        # ── Job persistence + notifications (issue #89) ─────────────────
        effective_job_path = _env.resolve_job_storage(job_storage_path)
        if effective_job_path:
            self._config.job_storage_path = effective_job_path
            logger.info("[%s] Job storage: %s", "maya", effective_job_path)
        elif effective_job_path == "":
            # Explicit "disable persistence" — clear the path that
            # ``DccServerBase._init_job_persistence`` may have set.
            self._config.job_storage_path = ""

        self._job_recovery: str = _env.resolve_job_recovery(job_recovery)
        # Propagate the chosen recovery policy into the inner Rust config so
        # the upstream JobRecoveryPolicy contract (dcc-mcp-core#567) actually
        # honours ``DCC_MCP_MAYA_JOB_RECOVERY=requeue`` instead of always
        # dropping interrupted jobs (issue #139).
        try:
            self._config.job_recovery = self._job_recovery
        except Exception as exc:  # noqa: BLE001
            logger.debug("[%s] Could not propagate job_recovery to inner config: %s", "maya", exc)
        if self._job_recovery == "requeue":
            logger.info("[%s] Job recovery policy: requeue idempotent interrupted jobs", "maya")

        # ── Workflow engine (issue #139 / dcc-mcp-core#565) ─────────────
        if _env.resolve_enable_workflows(enable_workflows):
            try:
                self._config.enable_workflows = True
                logger.info(
                    "[%s] Workflow engine enabled (workflows.run / .resume / .list_runs)",
                    "maya",
                )
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    "[%s] Could not enable workflows on inner config: %s",
                    "maya",
                    exc,
                )

        # Optional :class:`~dcc_mcp_maya.dispatcher.MayaUiDispatcher`
        # attached by the plugin (or by tests).  When set, :meth:`stop`
        # drains it before tearing the HTTP server down so any thread
        # blocked inside ``submit_callable`` returns within the normal
        # ``event.wait()`` budget instead of hanging indefinitely
        # (issue #85 / #89).
        self._maya_dispatcher: Any = None

    # ── Lifecycle additions ────────────────────────────────────────────

    def attach_dispatcher(self, dispatcher: Any) -> None:
        """Register a :class:`MayaUiDispatcher` for lifecycle integration.

        The server does not create the dispatcher itself because Maya needs
        control over when the :class:`MayaUiPump` is installed (that
        requires a live ``scriptJob``, which only makes sense inside a
        real interactive session).  Callers that manage a dispatcher
        should invoke :meth:`attach_dispatcher` **before**
        :meth:`register_builtin_actions` so that
        :meth:`DccServerBase.register_inprocess_executor` can wire
        the dispatcher before any tools are registered (issue #136).

        Passing ``None`` detaches a previously-registered dispatcher.

        .. note::

            This method also calls :meth:`DccServerBase.register_inprocess_executor`
            (issue #136) so that tools declaring ``affinity: main`` are
            executed on Maya's UI thread via the dispatcher, instead of
            falling back to a ``mayapy`` subprocess.
        """
        self._maya_dispatcher = dispatcher
        # Wire the in-process executor so that ``affinity: main`` tools
        # execute on the UI thread (issue #136).
        if dispatcher is not None:
            self.register_inprocess_executor(dispatcher)
        else:
            # Detach: clear the in-process executor so tools fall back to
            # subprocess execution (or inline if no dispatcher is attached).
            try:
                self._server.set_in_process_executor(None)
            except Exception as exc:  # noqa: BLE001
                logger.debug("[%s] Could not clear in-process executor: %s", self._dcc_name, exc)

    def stop(self) -> None:
        """Stop the HTTP server and drain any attached Maya dispatcher.

        Order matters: the dispatcher is drained **before** the HTTP
        server shuts down so any thread blocked inside
        ``submit_callable`` observes the drained outcome
        (``Interrupted``) and returns before the HTTP handler that
        originally enqueued the job gives up and closes the response.
        """
        dispatcher = self._maya_dispatcher
        if dispatcher is not None:
            try:
                shutdown = getattr(dispatcher, "shutdown", None)
                if callable(shutdown):
                    signalled = shutdown("Interrupted")
                    logger.info(
                        "[%s] dispatcher.shutdown signalled %s job(s)",
                        self._dcc_name,
                        signalled,
                    )
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    "[%s] Error draining Maya dispatcher during stop(): %s",
                    self._dcc_name,
                    exc,
                )
        super().stop()

    # ── Skill loading + executor wiring ────────────────────────────────

    def register_builtin_actions(
        self,
        extra_skill_paths: Optional[List[str]] = None,
        include_bundled: bool = True,
        minimal: Optional[bool] = None,
        strict_scan: Optional[bool] = None,
    ) -> "MayaMcpServer":
        """Discover skills, then optionally load only core skills.

        Phase 1 calls the base-class implementation to populate the
        :class:`SkillCatalog` (required for ``list_skills`` /
        ``search_skills`` / ``load_skill`` to work).  Phase 2 wires the
        in-process Python executor so loaded actions run inside the
        live Maya interpreter (issue #108).  Phase 3 selects which
        skills to fully load:

        * ``minimal=True`` (the default) → load only
          :data:`_skill_loader.MINIMAL_SKILLS` and deactivate the
          per-skill ``__group__`` stubs in
          :data:`_skill_loader.MINIMAL_DEACTIVATE_GROUPS`.
        * ``minimal=False`` → load every discovered skill (legacy).
        * ``DCC_MCP_MAYA_DEFAULT_TOOLS=skill1,skill2`` → load those
          skills only (overrides ``minimal``).

        When ``strict_scan=True`` (or ``DCC_MCP_MAYA_STRICT_SKILL_SCAN=1``),
        the discovery is followed by :func:`dcc_mcp_core.scan_and_load_strict`
        which raises :class:`ValueError` if any skill directory was
        silently skipped (issue #138).

        Returns ``self`` for chaining.
        """
        # Phase 1 — discover all skills.
        super().register_builtin_actions(
            extra_skill_paths=extra_skill_paths,
            include_bundled=include_bundled,
        )

        # Phase 1a — strict validation pass (issue #138). Raises
        # ``ValueError`` when any skill directory was silently skipped.
        if _env.resolve_strict_skill_scan(strict_scan):
            self._strict_skill_scan(extra_skill_paths, include_bundled)

        # Phase 2 — wire in-process executor for already-loaded actions.
        _executor.wire_in_process_executor(self)

        # Phase 3 — load skills selectively.
        is_minimal = _env.resolve_minimal_flag(minimal)
        custom_tools = _env.resolve_default_tools()

        if not is_minimal:
            _skill_loader.load_all_discovered_skills(self._server)
        elif custom_tools is not None:
            _skill_loader.load_minimal_skills(self._server, list(custom_tools.keys()))
        else:
            _skill_loader.load_minimal_skills(self._server, _skill_loader.MINIMAL_SKILLS)

        return self

    def _strict_skill_scan(
        self,
        extra_skill_paths: Optional[List[str]] = None,
        include_bundled: bool = True,
    ) -> None:
        """Re-scan with :func:`scan_and_load_strict` and raise on skipped dirs.

        Issue #138: surfaces silently-skipped skill directories at
        startup so packaging / CI failures are visible instead of
        appearing as missing tools at run-time.

        Raises
        ------
        ValueError
            When any skill directory failed validation. The exception
            message lists the offending directories.
        """
        from dcc_mcp_core import scan_and_load_strict  # noqa: PLC0415

        scan_paths = self.collect_skill_search_paths(
            extra_paths=extra_skill_paths,
            include_bundled=include_bundled,
            filter_existing=True,
        )
        try:
            scan_and_load_strict(extra_paths=scan_paths, dcc_name=self._dcc_name)
        except ValueError:
            raise
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "[%s] strict skill scan unavailable, falling back to lenient discovery: %s",
                self._dcc_name,
                exc,
            )

    def load_skill(self, skill_name: str) -> bool:
        """Load *skill_name* and register in-process handlers for its actions.

        Extends the base implementation so dynamically-loaded skills
        (via the ``load_skill`` MCP tool) also get in-process Python
        handlers — not just skills loaded during startup via
        :meth:`register_builtin_actions`.
        """
        try:
            action_names: List[str] = self._server.load_skill(skill_name) or []
        except Exception as exc:  # noqa: BLE001
            logger.debug("[%s] load_skill(%r) failed: %s", self._dcc_name, skill_name, exc)
            return False

        if action_names:
            newly_registered = _executor.register_inprocess_handlers(self, action_names)
            if newly_registered:
                logger.debug(
                    "[%s] load_skill(%r): registered %d in-process handler(s)",
                    self._dcc_name,
                    skill_name,
                    newly_registered,
                )
        return True

    # ── Maya version + transport wrappers ──────────────────────────────

    def _version_string(self) -> str:
        """Return the Maya version via :func:`_version_probe.get_maya_version_string`."""
        return _version_probe.get_maya_version_string()

    def bind_and_register(
        self,
        transport_manager: Any,
        version: Optional[str] = None,
        metadata: Optional[Any] = None,
    ) -> Any:
        """Register this Maya instance via ``TransportManager.bind_and_register``.

        Auto-detects the Maya version when ``version`` is omitted.  Returns
        the ``(instance_id, listener)`` tuple, or ``None`` when the call
        fails.  Delegates to :func:`_transport.bind_and_register`.
        """
        return _transport.bind_and_register(
            transport_manager,
            version=version,
            metadata=metadata,
        )

    @staticmethod
    def find_best_service(transport_manager: Any, dcc_type: str = "maya") -> Any:
        """Find the best available Maya MCP service via the transport manager.

        Static for backward-compat with callers that pass an externally-owned
        :class:`TransportManager` (issue #71 ergonomics).  Delegates to
        :func:`_transport.find_best_service`.
        """
        return _transport.find_best_service(transport_manager, dcc_type)

    @staticmethod
    def rank_services(transport_manager: Any, dcc_type: str = "maya") -> List[Any]:
        """Rank all active Maya MCP instances via the transport manager.

        Static for backward-compat (see :meth:`find_best_service`).  Delegates
        to :func:`_transport.rank_services`.
        """
        return _transport.rank_services(transport_manager, dcc_type)

    # ── Backwards-compat instance-method shims (issue #127) ────────────
    # Pre-#127 callers reached for these private instance methods; the
    # implementations now live in :mod:`_executor` but the names are
    # preserved here for one release cycle so external tests / patches
    # keep working without modification.

    def _wire_in_process_executor(self) -> None:
        """Backward-compat shim — see :func:`_executor.wire_in_process_executor`."""
        _executor.wire_in_process_executor(self)

    def _register_inprocess_handlers(self, action_names: List[str]) -> int:
        """Backward-compat shim — see :func:`_executor.register_inprocess_handlers`."""
        return _executor.register_inprocess_handlers(self, action_names)

    def _execute_in_process(
        self,
        script_path: str,
        params: dict,
        action_name: str,
    ) -> dict:
        """Backward-compat shim — see :func:`_executor.execute_in_process`."""
        return _executor.execute_in_process(self, script_path, params, action_name)


# ── Module-level singleton helpers ─────────────────────────────────────────

_server_lock = threading.Lock()
_instance_holder: List[Optional[MayaMcpServer]] = [None]
_server_instance: Optional[MayaMcpServer] = None


def start_server(
    port: int = 8765,
    register_builtins: bool = True,
    extra_skill_paths: Optional[List[str]] = None,
    include_bundled: bool = True,
    enable_hot_reload: bool = False,
    minimal: Optional[bool] = None,
    metrics_enabled: Optional[bool] = None,
    job_storage_path: Optional[str] = None,
    job_recovery: Optional[str] = None,
    dcc_pid: Optional[int] = None,
    dcc_window_title: Optional[str] = None,
    dcc_window_handle: Optional[int] = None,
    **kwargs: Any,
) -> Any:
    """Start (or return the already-running) Maya MCP server.

    Creates a module-level :class:`MayaMcpServer` singleton, optionally
    discovers all skills, and starts the MCP Streamable HTTP server.

    All keyword arguments accepted by :class:`MayaMcpServer` may be passed
    via ``**kwargs``.

    Returns
    -------
    Any
        ``McpServerHandle`` with ``.mcp_url()`` / ``.port`` / ``.shutdown()``.
    """
    global _server_instance

    dcc_window_title = _env.resolve_window_title(dcc_window_title)

    # Issue #125 — fix DCC_MCP_PYTHON_EXECUTABLE if it points at a GUI binary.
    from dcc_mcp_maya._pyexec import auto_correct as _auto_correct_pyexec  # noqa: PLC0415

    _auto_correct_pyexec()

    if register_builtins:
        with _server_lock:
            if _instance_holder[0] is not None and _instance_holder[0].is_running:
                return _instance_holder[0]._handle  # type: ignore[return-value]

            server = MayaMcpServer(
                port=port,
                metrics_enabled=metrics_enabled,
                job_storage_path=job_storage_path,
                job_recovery=job_recovery,
                dcc_pid=dcc_pid,
                dcc_window_title=dcc_window_title,
                dcc_window_handle=dcc_window_handle,
                **kwargs,
            )
            _instance_holder[0] = server
            server.register_builtin_actions(
                extra_skill_paths=extra_skill_paths,
                include_bundled=include_bundled,
                minimal=minimal,
            )

            # Hot-reload setup
            effective_hot_reload = enable_hot_reload
            if not effective_hot_reload:
                env_val = os.environ.get("DCC_MCP_MAYA_HOT_RELOAD", "").strip()
                effective_hot_reload = env_val == "1"
            if effective_hot_reload:
                try:
                    from dcc_mcp_core.hot_reload import HotReloader  # noqa: PLC0415

                    server._hot_reloader = HotReloader(server)  # type: ignore[attr-defined]
                    server._hot_reloader.start()  # type: ignore[attr-defined]
                except Exception as exc:
                    logger.debug("Hot-reload setup failed: %s", exc)

            handle = server.start()
            _server_instance = server
            return handle

    # No builtin registration — delegate to factory (backward compat)
    handle = create_dcc_server(
        instance_holder=_instance_holder,
        lock=_server_lock,
        server_class=MayaMcpServer,
        port=port,
        register_builtins=False,
        extra_skill_paths=extra_skill_paths,
        include_bundled=include_bundled,
        enable_hot_reload=enable_hot_reload,
        hot_reload_env_var="DCC_MCP_MAYA_HOT_RELOAD",
        metrics_enabled=metrics_enabled,
        job_storage_path=job_storage_path,
        job_recovery=job_recovery,
        dcc_pid=dcc_pid,
        dcc_window_title=dcc_window_title,
        dcc_window_handle=dcc_window_handle,
        **kwargs,
    )
    _server_instance = _instance_holder[0]
    return handle


def stop_server() -> None:
    """Stop the module-level singleton Maya MCP server."""
    global _server_instance
    with _server_lock:
        if _instance_holder[0] is not None:
            _instance_holder[0].stop()
            _instance_holder[0] = None
    _server_instance = None


# ── Backwards-compatibility shims ──────────────────────────────────────────
#
# Issue #127 split this module into ``_env`` / ``_executor`` /
# ``_skill_loader`` / ``_version_probe`` / ``_transport``.  The names below
# are re-exported here so any existing test, downstream patcher, or skill
# script that imports from ``dcc_mcp_maya.server`` keeps working without a
# code change.  Each shim is a *zero-overhead* alias — same callable, same
# behaviour.
#
# These names are NOT part of the public API documented in ``llms.txt``;
# new code should import from the dedicated submodules.

_run_skill_script = _executor.run_skill_script
_execute_in_process = _executor.execute_in_process
_register_inprocess_handlers = _executor.register_inprocess_handlers
_wire_in_process_executor = _executor.wire_in_process_executor

_load_minimal_skills = _skill_loader.load_minimal_skills
_load_all_discovered_skills = _skill_loader.load_all_discovered_skills
_MINIMAL_SKILLS = _skill_loader.MINIMAL_SKILLS
_MINIMAL_DEACTIVATE_GROUPS = _skill_loader.MINIMAL_DEACTIVATE_GROUPS

_resolve_minimal_flag = _env.resolve_minimal_flag
_resolve_default_tools = _env.resolve_default_tools
_ENV_MINIMAL = _env.ENV_MINIMAL
_ENV_DEFAULT_TOOLS = _env.ENV_DEFAULT_TOOLS
_ENV_METRICS = _env.ENV_METRICS
_ENV_JOB_STORAGE = _env.ENV_JOB_STORAGE
_ENV_JOB_RECOVERY = _env.ENV_JOB_RECOVERY
_DEFAULT_JOB_DB_FILENAME = _env.DEFAULT_JOB_DB_FILENAME

_maya_available = _version_probe.maya_available
