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
from dcc_mcp_maya import (
    _env,
    _executor,
    _project_tools,
    _skill_loader,
    _transport,
    _version_probe,
)
from dcc_mcp_maya.__version__ import __version__
from dcc_mcp_maya.capability_manifest import (
    MayaCapabilityManifestBuilder,
    build_manifest_payload,
    register_capability_mcp_tool,
)
from dcc_mcp_maya.context_snapshot import (
    MayaContextSnapshotProvider,
    collect_gateway_metadata,
)
from dcc_mcp_maya.host import MayaCallableDispatcher

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
        tool_exposure: Optional[str] = None,
        cursor_safe_tool_names: Optional[bool] = None,
        host_dispatcher: Optional[Any] = None,
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

        # ── Gateway tool-exposure mode (dcc-mcp-core#652, 0.14.22) ──────
        # ``DCC_MCP_MAYA_TOOL_EXPOSURE=slim|rest`` lets operators shrink
        # the gateway ``tools/list`` page to just the meta-tools.  When
        # unset we leave ``gateway_tool_exposure`` at whatever default
        # the installed core wheel ships (today ``"full"``) so behaviour
        # stays backward-compatible.
        effective_exposure = _env.resolve_tool_exposure(tool_exposure)
        if effective_exposure is not None:
            try:
                self._config.gateway_tool_exposure = effective_exposure
                logger.info(
                    "[%s] gateway_tool_exposure=%s",
                    "maya",
                    effective_exposure,
                )
            except Exception as exc:  # noqa: BLE001
                # Older core wheels that predate #652 won't expose this
                # attribute — that's fine; log at debug so a future
                # Maya-compatible downgrade stays quiet.
                logger.debug(
                    "[%s] gateway_tool_exposure unavailable on inner config: %s",
                    "maya",
                    exc,
                )

        # ── Cursor-safe tool names (dcc-mcp-core#656, 0.14.22) ──────────
        # Agents pointing Cursor/VS Code at a gateway want tool names
        # matching ``^[A-Za-z0-9_]+$``; set
        # ``DCC_MCP_MAYA_CURSOR_SAFE_TOOL_NAMES=0`` to opt out during a
        # migration window where SEP-986 dotted names are still needed.
        effective_cursor_safe = _env.resolve_cursor_safe_tool_names(cursor_safe_tool_names)
        if effective_cursor_safe is not None:
            try:
                self._config.gateway_cursor_safe_tool_names = bool(effective_cursor_safe)
                logger.info(
                    "[%s] gateway_cursor_safe_tool_names=%s",
                    "maya",
                    effective_cursor_safe,
                )
            except Exception as exc:  # noqa: BLE001
                logger.debug(
                    "[%s] gateway_cursor_safe_tool_names unavailable on inner config: %s",
                    "maya",
                    exc,
                )

        # Core 0.14.23 host dispatcher attached by the plugin/bootstrap.
        # It is wrapped as a callable dispatcher for the in-process skill
        # executor and attached directly to the Rust HTTP server so native
        # handlers and REST calls share the same main-thread path.
        self._maya_dispatcher: Any = None
        self._host_dispatcher: Any = None
        if host_dispatcher is not None:
            self.attach_dispatcher(host_dispatcher)
        else:
            self.register_inprocess_executor(None)

        # ── Context snapshot + capability manifest (issues #163 / #165) ──
        # Maya-specific context provider feeds both:
        #   * the core post-tool ``append_context_snapshot`` wrapper, and
        #   * the per-DCC ``GET /v1/context`` REST endpoint.
        # The builder is instantiated here so it shares lifetime with the
        # server and can be exposed via ``_capability_builder`` for tests.
        self._snapshot_provider_impl: MayaContextSnapshotProvider = MayaContextSnapshotProvider()
        try:
            self.set_context_snapshot_provider(self._snapshot_provider_impl)
        except Exception as exc:  # noqa: BLE001
            logger.debug("[%s] set_context_snapshot_provider failed: %s", "maya", exc)

        self._capability_builder: MayaCapabilityManifestBuilder = MayaCapabilityManifestBuilder(
            dcc_name="maya",
            skill_lister=self.list_skills,
            action_lister=self.list_actions,
            is_loaded=self.is_skill_loaded,
            skill_info_lister=self.get_skill_info,
        )

        # ── Project-state persistence (issue #576 / core 0.14.21) ──────
        # Populated by :meth:`register_builtin_actions` once the inner
        # registry is fully wired.  ``None`` means the surface was
        # disabled by the operator (``DCC_MCP_MAYA_PROJECT_TOOLS=0``)
        # or the underlying core call failed at registration time.
        self._project_tools: Optional[_project_tools.ProjectToolsIntegration] = None

    # ── Lifecycle additions ────────────────────────────────────────────

    def attach_dispatcher(self, dispatcher: Any) -> None:
        """Attach the core host dispatcher before skills are registered."""
        self._maya_dispatcher = dispatcher
        self._host_dispatcher = dispatcher
        if dispatcher is None:
            self.register_inprocess_executor(None)
            return

        native_attached = False
        attach = getattr(self._server, "attach_dispatcher", None)
        if callable(attach):
            try:
                attach(dispatcher)
                native_attached = True
            except RuntimeError as exc:
                logger.debug("[%s] host dispatcher already attached: %s", self._dcc_name, exc)
                native_attached = True
            except TypeError as exc:
                logger.debug("[%s] dispatcher is not a core Queue/BlockingDispatcher: %s", self._dcc_name, exc)
        if native_attached:
            self.register_inprocess_executor(MayaCallableDispatcher(dispatcher))
        else:
            self.register_inprocess_executor(dispatcher)

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

        # Phase 2 — load skills selectively. The in-process executor is
        # installed in __init__/attach_dispatcher before discovery, so core
        # owns routing for both eagerly loaded and dynamically loaded skills.
        is_minimal = _env.resolve_minimal_flag(minimal)
        custom_tools = _env.resolve_default_tools()

        if not is_minimal:
            _skill_loader.load_all_discovered_skills(self._server)
        elif custom_tools is not None:
            _skill_loader.load_minimal_skills(self._server, list(custom_tools.keys()))
        else:
            _skill_loader.load_minimal_skills(self._server, _skill_loader.MINIMAL_SKILLS)

        # Phase 3 — optionally expose the compact Maya capability manifest
        # as an MCP tool (issue #163).  Disabled by default because the
        # ``registry.register`` call bumps the registry generation, which
        # in multi-instance gateway mode can perturb __group__ stub
        # aggregation.  Opt in via env var ``DCC_MCP_MAYA_CAPABILITY_MCP_TOOL=1``
        # when you need it as a discoverable MCP tool.  The Python API
        # (``MayaMcpServer.build_capability_manifest`` and
        # ``publish_capability_snapshot``) remains available regardless.
        if os.environ.get("DCC_MCP_MAYA_CAPABILITY_MCP_TOOL", "0").strip() == "1":
            try:
                register_capability_mcp_tool(self, builder=self._capability_builder)
            except Exception as exc:  # noqa: BLE001
                logger.debug("[%s] capability manifest MCP tool registration failed: %s", "maya", exc)

        # Phase 4 — project-state persistence MCP/REST tools (issue #576).
        # Adds ``project.save`` / ``project.load`` / ``project.resume`` /
        # ``project.status`` so MCP agents can persist a Maya scene's
        # working set (loaded assets, active skills, active tool groups,
        # checkpoint IDs, free-form metadata) under
        # ``<scene_dir>/.dcc-mcp/project.json`` and rehydrate it across
        # Maya restarts.  The four handlers are pure filesystem
        # operations — no Maya state is touched — so they are safe to
        # register before any dispatcher is attached.  Opt out via
        # ``DCC_MCP_MAYA_PROJECT_TOOLS=0`` when an embedding host wants
        # to expose its own project surface.
        try:
            self._project_tools = _project_tools.attach_to_server(self)
        except Exception as exc:  # noqa: BLE001
            logger.debug("[%s] project tools registration failed: %s", "maya", exc)

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

        The gateway capability index refreshes on its own schedule via the
        FileRegistry heartbeat; we deliberately do **not** call
        :meth:`publish_capability_snapshot` here because an unconditional
        ``update_gateway_metadata`` during load_skill was observed to
        perturb the registry's group-stub bookkeeping in multi-instance
        runs (dropping ``__group__scene-management`` after a sibling
        skill was loaded).  Callers that must force an immediate
        publish can invoke :meth:`publish_capability_snapshot` directly.
        """
        try:
            self._server.load_skill(skill_name)
        except Exception as exc:  # noqa: BLE001
            logger.debug("[%s] load_skill(%r) failed: %s", self._dcc_name, skill_name, exc)
            return False
        return True

    def unload_skill(self, skill_name: str) -> bool:
        """Unload *skill_name*.

        Wraps :meth:`DccServerBase.unload_skill`.  Like :meth:`load_skill`,
        we avoid calling :meth:`publish_capability_snapshot` automatically —
        see the note there for the multi-instance rationale.
        """
        try:
            return bool(super().unload_skill(skill_name))
        except Exception as exc:  # noqa: BLE001
            logger.debug("[%s] unload_skill(%r) failed: %s", self._dcc_name, skill_name, exc)
            return False

    # ── Gateway capability manifest + metadata (issues #163 / #165) ────

    def start(self) -> Any:
        """Start the HTTP server.

        The base class ``start()`` brings the Rust ``McpHttpServer`` up.
        The initial ``update_gateway_metadata`` publish is intentionally
        **deferred** until the first ``load_skill`` / ``unload_skill``
        call (or an explicit :meth:`publish_capability_snapshot`): pushing
        a half-formed snapshot during startup can clobber fresh
        FileRegistry entries written by sibling Maya instances that
        registered before the local election won.  The gateway's own
        heartbeat (5 s) publishes our metadata anyway.
        """
        return super().start()

    def publish_capability_snapshot(self, *, reason: str = "manual") -> bool:
        """Push current Maya context into the gateway registry.

        Returns ``True`` when :meth:`update_gateway_metadata` succeeded.  No
        exception escapes — this is a best-effort housekeeping call.

        ``reason`` is only used for log lines; it lets us trace **why** the
        capability index was bumped (startup / load_skill / unload_skill /
        manual).

        Safety
        ------
        When the context snapshot reports no actionable Maya state
        (``available=False``, empty scene, no version), the call is
        short-circuited.  This prevents clobbering existing FileRegistry
        entries with "empty" metadata during startup — the registry will
        pick up accurate values on the first meaningful scene change
        instead.
        """
        if not self.is_running:
            return False
        gateway_port = getattr(self._config, "gateway_port", 0)
        if not gateway_port or gateway_port <= 0:
            # Single-process mode: nothing to publish to.
            return False
        try:
            meta = collect_gateway_metadata(self._snapshot_provider_impl)
        except Exception as exc:  # noqa: BLE001
            logger.debug("[%s] capability snapshot: provider failed: %s", self._dcc_name, exc)
            return False

        # Short-circuit when there's nothing useful to push — avoids
        # clobbering fresh FileRegistry entries with empty values during
        # headless/standalone startup.
        if not any((meta.get("scene"), meta.get("version"), meta.get("display_name"))):
            logger.debug(
                "[%s] capability snapshot (%s): skipped — no actionable Maya state",
                self._dcc_name,
                reason,
            )
            return False

        try:
            ok = self.update_gateway_metadata(
                scene=meta.get("scene"),
                version=meta.get("version"),
                documents=meta.get("documents"),
                display_name=meta.get("display_name"),
            )
        except Exception as exc:  # noqa: BLE001
            logger.debug(
                "[%s] update_gateway_metadata failed (%s): %s",
                self._dcc_name,
                reason,
                exc,
            )
            return False

        if ok:
            logger.debug(
                "[%s] published capability snapshot (%s): scene=%s version=%s",
                self._dcc_name,
                reason,
                meta.get("scene"),
                meta.get("version"),
            )
        return bool(ok)

    def build_capability_manifest(self, *, loaded_only: bool = False) -> dict:
        """Return the compact Maya capability manifest as a dict.

        Mirrors the payload emitted by the ``dcc_capability_manifest`` MCP
        tool so tests (and programmatic callers) can inspect it without
        going through HTTP.
        """
        records = self._capability_builder.build()
        if loaded_only:
            records = [r for r in records if r.loaded]
        instance_id = getattr(self, "instance_id", None)
        scene = getattr(self._config, "scene", None)
        version = getattr(self._config, "dcc_version", None)
        return build_manifest_payload(
            records,
            dcc_name="maya",
            dcc_version=version,
            scene=scene,
            instance_id=instance_id,
        )

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

    def _execute_in_process(
        self,
        script_path: str,
        params: dict,
        action_name: str,
    ) -> dict:
        """Execute a skill script directly for unit tests and internal probes."""
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
    host_dispatcher: Optional[Any] = None,
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
                host_dispatcher=host_dispatcher,
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
        host_dispatcher=host_dispatcher,
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
