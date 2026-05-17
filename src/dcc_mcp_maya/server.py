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
from dataclasses import dataclass
from pathlib import Path
from typing import Any, List, Optional

# Import third-party modules
from dcc_mcp_core import DccServerOptions, HostExecutionBridge, scan_and_load_strict
from dcc_mcp_core.factory import create_dcc_server
from dcc_mcp_core.server_base import DccServerBase

# Import local modules
from dcc_mcp_maya import (
    _env,
    _executor,
    _project_tools,
    _readiness,
    _registration,
    _resources,
    _skill_loader,
    _transport,
    _version_probe,
)
from dcc_mcp_maya.__version__ import __version__
from dcc_mcp_maya._pyexec import auto_correct as _auto_correct_pyexec
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


def _logger_has_closed_stream(target_logger: logging.Logger) -> bool:
    """Return true when a handler in the propagation chain cannot write."""
    current: Optional[logging.Logger] = target_logger
    while current is not None:
        for handler in current.handlers:
            stream = getattr(handler, "stream", None)
            if stream is not None and getattr(stream, "closed", False):
                return True
        if not current.propagate:
            break
        current = current.parent
    return False


def _log_dispatcher_shutdown(dcc_name: str, signalled: Any) -> None:
    """Best-effort dispatcher shutdown log for late interpreter teardown."""
    if _logger_has_closed_stream(logger):
        return
    logger.info(
        "[%s] dispatcher.shutdown signalled %s job(s)",
        dcc_name,
        0 if signalled is None else signalled,
    )


@dataclass
class MayaServerOptions:
    """Maya adapter options collapsed for the core 0.15.9 server contract."""

    port: int = 8765
    server_name: str = "maya-mcp"
    server_version: str = DEFAULT_SERVER_VERSION
    gateway_port: Optional[int] = None
    registry_dir: Optional[str] = None
    dcc_version: Optional[str] = None
    scene: Optional[str] = None
    enable_gateway_failover: Optional[bool] = None
    metrics_enabled: Optional[bool] = None
    job_storage_path: Optional[str] = None
    job_recovery: Optional[str] = None
    dcc_pid: Optional[int] = None
    dcc_window_title: Optional[str] = None
    dcc_window_handle: Optional[int] = None
    enable_workflows: Optional[bool] = None
    host_dispatcher: Optional[Any] = None
    readiness_timeout_secs: Optional[int] = None

    def to_core_options(self) -> DccServerOptions:
        return DccServerOptions.from_env(
            dcc_name="maya",
            builtin_skills_dir=_BUILTIN_SKILLS_DIR,
            port=self.port,
            server_name=self.server_name,
            server_version=self.server_version,
            gateway_port=self.gateway_port,
            registry_dir=self.registry_dir,
            dcc_version=self.dcc_version,
            scene=self.scene,
            enable_gateway_failover=_env.resolve_enable_gateway_failover(
                self.enable_gateway_failover,
                default=True,
            ),
            dcc_pid=self.dcc_pid,
            dcc_window_title=self.dcc_window_title,
            dcc_window_handle=self.dcc_window_handle,
        )


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
        enable_gateway_failover: Optional[bool] = None,
        metrics_enabled: Optional[bool] = None,
        job_storage_path: Optional[str] = None,
        job_recovery: Optional[str] = None,
        dcc_pid: Optional[int] = None,
        dcc_window_title: Optional[str] = None,
        dcc_window_handle: Optional[int] = None,
        enable_workflows: Optional[bool] = None,
        host_dispatcher: Optional[Any] = None,
        readiness_timeout_secs: Optional[int] = None,
        options: Optional[MayaServerOptions] = None,
    ) -> None:
        if options is None:
            options = MayaServerOptions(
                port=port,
                server_name=server_name,
                server_version=server_version,
                gateway_port=gateway_port,
                registry_dir=registry_dir,
                dcc_version=dcc_version,
                scene=scene,
                enable_gateway_failover=enable_gateway_failover,
                metrics_enabled=metrics_enabled,
                job_storage_path=job_storage_path,
                job_recovery=job_recovery,
                dcc_pid=dcc_pid,
                dcc_window_title=dcc_window_title,
                dcc_window_handle=dcc_window_handle,
                enable_workflows=enable_workflows,
                host_dispatcher=host_dispatcher,
                readiness_timeout_secs=readiness_timeout_secs,
            )

        super().__init__(options=options.to_core_options())

        metrics_enabled = options.metrics_enabled
        job_storage_path = options.job_storage_path
        job_recovery = options.job_recovery
        enable_workflows = options.enable_workflows
        gateway_port = options.gateway_port
        enable_gateway_failover = _env.resolve_enable_gateway_failover(
            options.enable_gateway_failover,
            default=True,
        )
        host_dispatcher = options.host_dispatcher
        readiness_timeout_secs = options.readiness_timeout_secs

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
        self._config.job_recovery = self._job_recovery
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

        if gateway_port == 0 or (gateway_port is None and not enable_gateway_failover):
            self._config.gateway_port = 0

        # Host dispatcher attached by the plugin/bootstrap.  The core
        # HostExecutionBridge is the single adapter-facing execution path
        # for direct host callables and in-process skill scripts.
        self._maya_dispatcher: Any = None
        self._host_dispatcher: Any = None
        self._execution_bridge: HostExecutionBridge

        # ── Runtime readiness binder (issue #184) ──────────────────────
        # Constructed *before* dispatcher attachment so ``attach_dispatcher``
        # can re-bind through ``self._readiness`` unconditionally — no
        # ``getattr`` guard, no ``try/except``.  Bound for real at the end
        # of ``__init__`` once the executor wiring is settled.
        self._readiness_timeout_secs: Optional[int] = _readiness.resolve_readiness_timeout_secs(readiness_timeout_secs)
        self._readiness: _readiness.ReadinessBinder = _readiness.ReadinessBinder(
            timeout_secs=self._readiness_timeout_secs,
        )

        if host_dispatcher is None:
            host_dispatcher = self._default_standalone_dispatcher()

        if host_dispatcher is not None:
            self.attach_dispatcher(host_dispatcher)
        else:
            self._register_execution_bridge(None)

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

        # Bind the readiness binder now that the executor and dispatcher
        # state are settled.  ``attach_dispatcher`` above may have already
        # bound it (``bound_server is self``); :meth:`bind` is idempotent
        # so calling again is a no-op when the server is unchanged.
        self._readiness.bind(self)

        # ── Resource publishing (issue #187 / core 0.15.0) ─────────────
        # Populated by :meth:`register_builtin_actions` once the inner
        # ``McpHttpServer`` is fully constructed.  Hosts every Maya
        # call into ``server._server.resources()`` (per the resources-
        # API memory rule) so skill scripts and plugin code never
        # touch the raw ``ResourceHandle`` directly.
        self._resources: Optional[_resources.MayaResourceBinder] = None

    # ── Lifecycle additions ────────────────────────────────────────────

    @staticmethod
    def _default_standalone_dispatcher() -> Optional[Any]:
        """Use the batch dispatcher automatically inside real mayapy.

        Plain Python and unit tests keep the historical inline path.  Real
        mayapy exposes ``maya.cmds`` and reports ``about(batch=True)``; in
        that environment we still need one serialized gateway into Maya APIs.
        """
        try:
            import maya.cmds as cmds  # noqa: PLC0415
        except Exception:  # noqa: BLE001
            return None
        try:
            is_batch = bool(cmds.about(batch=True))
        except Exception:  # noqa: BLE001
            return None
        if not is_batch:
            return None
        try:
            from dcc_mcp_maya.dispatcher import MayaStandaloneDispatcher  # noqa: PLC0415
        except Exception:  # noqa: BLE001
            return None
        return MayaStandaloneDispatcher()

    def attach_dispatcher(self, dispatcher: Any) -> None:
        """Attach the Maya host dispatcher before skills are registered."""
        self._maya_dispatcher = dispatcher
        self._host_dispatcher = dispatcher
        if dispatcher is None:
            self._register_execution_bridge(None)
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
                logger.debug("[%s] dispatcher is not a native core dispatcher: %s", self._dcc_name, exc)
        bridge_dispatcher = MayaCallableDispatcher(dispatcher) if native_attached else dispatcher
        self._register_execution_bridge(bridge_dispatcher)

        # ── Readiness (issue #184) ─────────────────────────────────────
        # Re-bind through the readiness binder so a late
        # ``attach_dispatcher`` (e.g. plugin bootstrap wires the
        # dispatcher after ``MayaMcpServer.__init__`` ran) flips
        # ``dispatcher=true`` and schedules the dcc probe on the new
        # dispatcher.  The binder is always constructed before the
        # first dispatcher attachment inside ``__init__``.
        self._readiness.bound_server = None  # force re-bind
        self._readiness.bind(self)

    def _register_execution_bridge(self, dispatcher: Any) -> None:
        self._execution_bridge = HostExecutionBridge(
            dispatcher=dispatcher,
            runner=_executor.run_skill_script,
            default_thread_affinity="main",
        )
        self.register_host_execution_bridge(self._execution_bridge)

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
                    try:
                        signalled = shutdown("Interrupted")
                    except TypeError:
                        signalled = shutdown()
                    _log_dispatcher_shutdown(self._dcc_name, signalled)
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    "[%s] Error draining Maya dispatcher during stop(): %s",
                    self._dcc_name,
                    exc,
                )

        # Detach scriptJobs and pending throttle timers before the inner
        # Rust server tears down (issue #187).
        if self._resources is not None:
            try:
                self._resources.unbind()
            except Exception as exc:  # noqa: BLE001
                logger.debug("[%s] resources.unbind failed: %s", self._dcc_name, exc)

        super().stop()

    # ── Skill loading + executor wiring ────────────────────────────────

    def register_builtin_actions(
        self,
        extra_skill_paths: Optional[List[str]] = None,
        include_bundled: bool = True,
        minimal: Optional[bool] = None,
        strict_scan: Optional[bool] = None,
    ) -> "MayaMcpServer":
        """Discover Maya skills and attach Maya-specific core integrations."""
        context = _registration.RegistrationContext(
            server=self,
            extra_skill_paths=extra_skill_paths,
            include_bundled=include_bundled,
            minimal=minimal,
            strict_scan=strict_scan,
        )
        report = _registration.run_registration_phases(_registration.default_registration_phases(), context)
        self._registration_report = report
        logger.info(
            "[%s] builtin action registration completed success=%s phases=%s elapsed=%.3fs",
            self._dcc_name,
            report.success,
            len(report.outcomes),
            report.elapsed_secs,
        )
        return self

    def _register_core_builtin_actions(self, context: _registration.RegistrationContext) -> None:
        super().register_builtin_actions(
            extra_skill_paths=context.extra_skill_paths,
            include_bundled=context.include_bundled,
            minimal_mode=self._build_minimal_mode_config(context.minimal),
        )

    def _register_recipes_tools(self, context: _registration.RegistrationContext) -> None:
        """Register ``recipes__*`` tools so ``metadata.dcc-mcp.recipes`` files are agent-readable."""
        try:
            from dcc_mcp_core.recipes import register_recipes_tools
        except ImportError as exc:
            logger.debug("[%s] recipes tools skipped (import): %s", self._dcc_name, exc)
            return
        try:
            skills = self._scan_skill_metadata_for_sidecars(context)
            register_recipes_tools(self._server, skills=skills, dcc_name=self._dcc_name)
        except Exception as exc:  # noqa: BLE001
            logger.debug("[%s] register_recipes_tools failed: %s", self._dcc_name, exc)

    def _register_skill_reference_docs_tools(self, context: _registration.RegistrationContext) -> None:
        """Register ``skill_refs__*`` for arbitrary reference Markdown/text beside a skill."""
        try:
            from dcc_mcp_core.skill_reference_docs import register_skill_reference_docs_tools
        except ImportError as exc:
            logger.debug("[%s] skill_refs tools skipped (import): %s", self._dcc_name, exc)
            return
        try:
            skills = self._scan_skill_metadata_for_sidecars(context)
            register_skill_reference_docs_tools(self._server, skills=skills, dcc_name=self._dcc_name)
        except Exception as exc:  # noqa: BLE001
            logger.debug("[%s] register_skill_reference_docs_tools failed: %s", self._dcc_name, exc)

    def _scan_skill_metadata_for_sidecars(self, context: _registration.RegistrationContext) -> List[Any]:
        """Return ``SkillMetadata`` list aligned with ``collect_skill_search_paths`` (read-only scan)."""
        from dcc_mcp_core import scan_and_load_lenient

        paths = self.collect_skill_search_paths(
            extra_paths=context.extra_skill_paths,
            include_bundled=context.include_bundled,
            filter_existing=True,
        )
        extra = paths if paths else None
        skills, _skipped = scan_and_load_lenient(extra_paths=extra, dcc_name=self._dcc_name)
        return skills

    def _build_minimal_mode_config(self, minimal: Optional[bool]) -> Any:
        """Return Maya's core MinimalModeConfig or ``None`` for full mode."""
        if minimal is False:
            return None
        return _skill_loader.build_minimal_mode_config()

    def _run_strict_skill_scan_if_enabled(
        self,
        strict_scan: Optional[bool],
        extra_skill_paths: Optional[List[str]],
        include_bundled: bool,
    ) -> None:
        if _env.resolve_strict_skill_scan(strict_scan):
            self._strict_skill_scan(extra_skill_paths, include_bundled)

    def _register_capability_manifest_tool(self) -> None:
        try:
            register_capability_mcp_tool(self, builder=self._capability_builder)
        except Exception as exc:  # noqa: BLE001
            logger.debug("[%s] capability manifest MCP tool registration failed: %s", "maya", exc)

    def _attach_project_tools(self) -> None:
        try:
            self._project_tools = _project_tools.attach_to_server(self)
        except Exception as exc:  # noqa: BLE001
            logger.debug("[%s] project tools registration failed: %s", "maya", exc)

    def _attach_resources(self) -> None:
        try:
            self._resources = _resources.install_resources(
                self,
                snapshot_provider=self._snapshot_provider_impl.collect,
                busy_checker=_executor.is_busy,
            )
        except Exception as exc:  # noqa: BLE001
            logger.debug("[%s] resources registration failed: %s", "maya", exc)

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

    def search_actions(self, *args: Any, **kwargs: Any) -> list:
        # Inject Maya-specific default for dcc_name
        if "dcc_name" not in kwargs:
            kwargs["dcc_name"] = self._dcc_name
        try:
            return list(super().search_actions(*args, **kwargs))
        except Exception as exc:  # noqa: BLE001
            logger.debug("[%s] search_actions failed: %s", self._dcc_name, exc)
            return []

    def unregister_skill(self, name: str, dcc_name: Optional[str] = None) -> None:
        try:
            super().unregister_skill(name, dcc_name=dcc_name)
        except Exception as exc:  # noqa: BLE001
            logger.debug("[%s] unregister_skill(%r) failed: %s", self._dcc_name, name, exc)

    def search_skills(
        self, query: Optional[str] = None, tags: Optional[list] = None, dcc: Optional[str] = None
    ) -> list:
        # Inject Maya-specific default for dcc
        if dcc is None:
            dcc = self._dcc_name
        try:
            return list(super().search_skills(query=query, tags=tags, dcc=dcc))
        except Exception as exc:  # noqa: BLE001
            logger.debug("[%s] search_skills failed: %s", self._dcc_name, exc)
            return []

    def get_skill_categories(self) -> list:
        try:
            return list(super().get_skill_categories())
        except Exception as exc:  # noqa: BLE001
            logger.debug("[%s] get_skill_categories failed: %s", self._dcc_name, exc)
            return []

    def get_skill_tags(self, dcc_name: str = "maya") -> list:
        try:
            return list(super().get_skill_tags(dcc_name=dcc_name))
        except Exception as exc:  # noqa: BLE001
            logger.debug("[%s] get_skill_tags failed: %s", self._dcc_name, exc)
            return []

    def is_skill_loaded(self, name: str) -> bool:
        try:
            return bool(super().is_skill_loaded(name))
        except Exception as exc:  # noqa: BLE001
            logger.debug("[%s] is_skill_loaded(%r) failed: %s", self._dcc_name, name, exc)
            return False

    def get_skill_info(self, name: str) -> Any:
        try:
            return super().get_skill_info(name)
        except Exception as exc:  # noqa: BLE001
            logger.debug("[%s] get_skill_info(%r) failed: %s", self._dcc_name, name, exc)
            return None

    # ── Lifecycle: start() + gateway capability metadata ───────────────

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

    def _upgrade_to_gateway(self) -> bool:
        """Promote to gateway on the Maya UI thread when possible.

        :class:`~dcc_mcp_core.gateway_election.DccGatewayElection` runs on a
        daemon thread. The default implementation shuts down the inner HTTP
        handle and calls ``McpHttpServer.start()``, which uses Tokio
        ``Runtime::block_on`` — that path must match the initial bootstrap
        thread (Maya main thread) so promotion and MCP restart stay reliable.
        """
        try:
            import maya.cmds as cmds  # noqa: PLC0415
            import maya.utils as mu  # noqa: PLC0415
        except ImportError:
            return super()._upgrade_to_gateway()

        try:
            if bool(cmds.about(batch=True)):
                return super()._upgrade_to_gateway()
        except Exception as exc:  # noqa: BLE001
            logger.warning("[%s] cmds.about(batch) failed during gateway promotion: %s", self._dcc_name, exc)
            return super()._upgrade_to_gateway()

        try:
            parent_upgrade = super()._upgrade_to_gateway
            return bool(mu.executeInMainThreadWithResult(parent_upgrade))
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "[%s] executeInMainThreadWithResult gateway promotion failed: %s — falling back",
                self._dcc_name,
                exc,
            )
            return super()._upgrade_to_gateway()

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

    # ── Readiness (issue #184) ─────────────────────────────────────────

    def readiness_report(self) -> dict:
        """Return the current three-state readiness snapshot as a dict.

        Keys: ``process`` / ``dispatcher`` / ``dcc`` (all booleans).  The
        backend is considered ready only when all three are ``True``.
        During Maya's boot window the expected sequence is::

            {"process": True, "dispatcher": False, "dcc": False}
            {"process": True, "dispatcher": True,  "dcc": False}  # after executor attached
            {"process": True, "dispatcher": True,  "dcc": True}   # after first main-thread pump

        See :mod:`dcc_mcp_maya._readiness` for the full contract.
        """
        return self._readiness.report()

    @property
    def readiness(self) -> _readiness.ReadinessBinder:
        """Expose the :class:`ReadinessBinder` for tests and orchestrators.

        The underlying three-state probe is available as
        ``server.readiness.probe`` (a :class:`dcc_mcp_core.ReadinessProbe`).
        """
        return self._readiness

    # ── Gateway capability manifest + metadata (issues #163 / #165) ────

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

        Delegates to :func:`_transport.find_best_service` for callers that
        operate on an externally-owned :class:`TransportManager`.
        """
        return _transport.find_best_service(transport_manager, dcc_type)

    @staticmethod
    def rank_services(transport_manager: Any, dcc_type: str = "maya") -> List[Any]:
        """Rank all active Maya MCP instances via the transport manager.

        Delegates to :func:`_transport.rank_services` for callers that operate
        on an externally-owned :class:`TransportManager`.
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
    readiness_timeout_secs: Optional[int] = None,
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
                readiness_timeout_secs=readiness_timeout_secs,
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
                    # Optional core feature: keep this import local so normal startup
                    # does not fail when a core build omits hot_reload support.
                    from dcc_mcp_core.hot_reload import HotReloader  # noqa: PLC0415

                    server._hot_reloader = HotReloader(server)  # type: ignore[attr-defined]
                    server._hot_reloader.start()  # type: ignore[attr-defined]
                except Exception as exc:
                    logger.debug("Hot-reload setup failed: %s", exc)

            handle = server.start()
            _server_instance = server
            return handle

    # No builtin registration — delegate to the shared core factory path.
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
        readiness_timeout_secs=readiness_timeout_secs,
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
