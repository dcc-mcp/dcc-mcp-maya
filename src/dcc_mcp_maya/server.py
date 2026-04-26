"""MayaMcpServer — embedded MCP Streamable HTTP server for Maya.

Extends :class:`dcc_mcp_core.server_base.DccServerBase` with Maya-specific
skill path discovery and version detection.

All generic logic (skill registration, hot-reload, gateway failover,
tool registry, lifecycle) is provided by the base class.

Flow::

    server = MayaMcpServer(port=8765)
    server.register_builtin_actions()   # discover skills; load on demand
    handle = server.start()
    print(handle.mcp_url())             # http://127.0.0.1:8765/mcp
    handle.shutdown()

Or via the module-level singleton helper::

    import dcc_mcp_maya
    handle = dcc_mcp_maya.start_server(port=8765)
    print(handle.mcp_url())

Search path resolution (highest → lowest priority):

1. ``extra_skill_paths`` supplied by the caller
2. Built-in skills shipped with this package  (``src/dcc_mcp_maya/skills/``)
3. ``DCC_MCP_MAYA_SKILL_PATHS`` environment variable (Maya-specific)
4. ``DCC_MCP_SKILL_PATHS`` environment variable (global fallback)
5. Platform default  (``dcc_mcp_core.get_skills_dir()``)
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
from dcc_mcp_maya.__version__ import __version__

logger = logging.getLogger(__name__)

DEFAULT_SERVER_VERSION = __version__

# Built-in skills directory shipped with this package
_BUILTIN_SKILLS_DIR = Path(__file__).parent / "skills"

# ── Minimal-mode defaults ────────────────────────────────────────────────────
# When minimal=True (the default), only these skills are loaded at startup;
# all others remain as ``__skill__<name>`` stubs in ``tools/list``.
_MINIMAL_SKILLS: List[str] = ["maya-scripting", "maya-scene"]

# Groups to deactivate when running in minimal mode.
# Keys are skill names; values are lists of group names to deactivate.
# After ``load_skill`` the server calls ``deactivate_group`` for each listed
# group, collapsing those tools into ``__group__<name>`` stubs.
_MINIMAL_DEACTIVATE_GROUPS: dict[str, list[str]] = {
    "maya-scripting": ["extended"],
    "maya-scene": ["scene-management"],
}

# Environment variable overrides:
#   DCC_MCP_MAYA_MINIMAL=0          → pre-load all bundled skills (legacy)
#   DCC_MCP_MAYA_DEFAULT_TOOLS="execute_python,get_scene_info,..."
#       → customise which skills (and optionally which groups) are active
#         at startup.
#   DCC_MCP_MAYA_METRICS=1          → enable Prometheus /metrics endpoint
#       (issue #87; requires wheel built with prometheus feature).
#   DCC_MCP_MAYA_JOB_STORAGE=<path> → SQLite job-persistence file path
#       (issue #89; default: <platform_data_dir>/dcc-mcp-maya/jobs.db).
#   DCC_MCP_MAYA_JOB_RECOVERY=requeue
#       → re-queue idempotent interrupted jobs on startup (issue #89;
#         default behaviour is "drop" as documented in the issue).
#   DCC_MCP_MAYA_WINDOW_TITLE=...
#       → passed as ``dcc_window_title`` to :class:`MayaMcpServer` (diagnostics
#         / screenshot routing; dcc-mcp-core 0.14+).  The Maya plugin sets this
#         when the env var is non-empty.
_ENV_MINIMAL = "DCC_MCP_MAYA_MINIMAL"
_ENV_DEFAULT_TOOLS = "DCC_MCP_MAYA_DEFAULT_TOOLS"
_ENV_METRICS = "DCC_MCP_MAYA_METRICS"
_ENV_JOB_STORAGE = "DCC_MCP_MAYA_JOB_STORAGE"
_ENV_JOB_RECOVERY = "DCC_MCP_MAYA_JOB_RECOVERY"

# Default SQLite file for job persistence — inside the platform data directory
# so it survives upgrades and is shared across Maya sessions on the same user
# account (issue #89).
_DEFAULT_JOB_DB_FILENAME = "jobs.db"


def _resolve_minimal_flag(minimal: Optional[bool]) -> bool:
    """Resolve the minimal-mode flag from the argument and env vars.

    Priority:
    1. Explicit ``minimal`` argument (not None)
    2. ``DCC_MCP_MAYA_MINIMAL`` env var (``"0"`` → False, ``"1"`` → True)
    3. Default: True
    """
    if minimal is not None:
        return minimal
    env_val = os.environ.get(_ENV_MINIMAL)
    if env_val is not None:
        return env_val.strip() != "0"
    return True


def _resolve_default_tools() -> Optional[dict[str, list[str]]]:
    """Parse ``DCC_MCP_MAYA_DEFAULT_TOOLS`` env var into skill→groups map.

    The env var format is a comma-separated list of skill names.  When
    present, only the listed skills are loaded at startup, and groups
    not named in the value are deactivated.

    Returns None if the env var is not set.
    """
    raw = os.environ.get(_ENV_DEFAULT_TOOLS)
    if not raw:
        return None
    result: dict[str, list[str]] = {}
    for token in raw.split(","):
        token = token.strip()
        if not token:
            continue
        # No group-level granularity in env var for now — just skill names
        result.setdefault(token, [])
    return result


def _maya_available() -> bool:
    """Return True if Maya is importable in this Python environment."""
    try:
        import maya.cmds  # noqa: F401

        return True
    except ImportError:
        return False


def _run_skill_script(script_path: str, params: dict) -> dict:
    """Load and execute a skill script in the current Python process.

    Implements the ``main(**params)`` calling convention used by all
    ``dcc-mcp-maya`` skill scripts.  The ``if __name__ == "__main__":
    run_main(main)`` guard is intentionally **not** triggered so that
    parameters are forwarded directly without subprocess stdout.

    Parameters
    ----------
    script_path:
        Path to the skill Python script.
    params:
        Keyword arguments forwarded to ``main(**params)``.

    Returns
    -------
    dict
        The ``{"success": ..., "message": ..., ...}`` result dict.
    """
    import importlib.util  # noqa: PLC0415

    spec = importlib.util.spec_from_file_location("_maya_skill_script", script_path)
    if spec is None or spec.loader is None:
        return {"success": False, "message": "Cannot load skill script: {}".format(script_path)}

    mod = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(mod)  # type: ignore[union-attr]
    except SystemExit:
        pass
    except Exception as exc:  # noqa: BLE001
        try:
            from dcc_mcp_core.skill import skill_exception  # noqa: PLC0415

            return skill_exception(exc, message="Error loading skill script: {}".format(script_path))
        except ImportError:
            return {"success": False, "message": "Error loading {}: {}".format(script_path, exc)}

    if hasattr(mod, "__mcp_result__"):
        return mod.__mcp_result__  # type: ignore[return-value]

    main_fn = getattr(mod, "main", None)
    if main_fn is None:
        return {
            "success": False,
            "message": "Skill script has no main() entry point: {}".format(script_path),
        }

    try:
        result = main_fn(**params)
        return result if isinstance(result, dict) else {"success": True, "message": str(result)}
    except SystemExit:
        return getattr(mod, "__mcp_result__", {"success": True, "message": "Script executed"})
    except Exception as exc:  # noqa: BLE001
        try:
            from dcc_mcp_core.skill import skill_exception  # noqa: PLC0415

            return skill_exception(exc)
        except ImportError:
            return {"success": False, "message": str(exc)}


class MayaMcpServer(DccServerBase):
    """MCP Streamable HTTP server embedded inside Maya.

    Thin subclass of :class:`~dcc_mcp_core.server_base.DccServerBase`.
    All skill management, hot-reload, gateway election, and lifecycle
    logic is inherited.  This class adds only:

    - Maya builtin skills directory (``skills/``)
    - Maya version detection via ``cmds.about(version=True)``
    - Minimal-mode startup: only core skills are loaded, the rest
      remain as ``__skill__`` stubs for progressive activation
    - ``register_builtin_actions()`` (minimal / full skill loading); instance-bound
      diagnostic IPC + MCP tools are registered in
      :meth:`~dcc_mcp_core.server_base.DccServerBase.start` (0.14+)
    - Maya-specific TransportManager wrappers
      (``bind_and_register``, ``find_best_service``, ``rank_services``)
    - Prometheus ``/metrics`` endpoint support (issue #87)
    - SQLite job persistence and startup recovery policy (issue #89)

    Example::

        server = MayaMcpServer(port=8765)
        server.register_builtin_actions()
        handle = server.start()
        print(handle.mcp_url())    # http://127.0.0.1:8765/mcp
        handle.shutdown()

    Prometheus metrics (issue #87)::

        # Enable via constructor flag …
        server = MayaMcpServer(port=8765, metrics_enabled=True)
        # … or via environment variable:
        # DCC_MCP_MAYA_METRICS=1 python -m dcc_mcp_maya

        # Then scrape:
        # curl http://127.0.0.1:8765/metrics

    Job persistence and recovery (issue #89)::

        # Enable SQLite job storage — jobs survive Maya restarts
        server = MayaMcpServer(
            port=8765,
            job_storage_path="/path/to/maya-jobs.db",
            job_recovery="requeue",   # "drop" (default) or "requeue"
        )

    Args:
        port: TCP port to listen on.  Use ``0`` for a random available port.
        server_name: Name reported in MCP ``initialize`` response.
        server_version: Version reported in MCP ``initialize`` response.
        gateway_port: Port for first-wins gateway competition.  ``None``
            reads ``DCC_MCP_GATEWAY_PORT`` env var; ``0`` disables.
        registry_dir: Directory for the shared ``FileRegistry`` JSON file.
        dcc_version: Maya version string reported to the registry.
        scene: Currently open scene file path reported to the registry.
        enable_gateway_failover: Enable automatic gateway failover election.
        metrics_enabled: Enable the Prometheus ``/metrics`` endpoint.
            ``None`` reads ``DCC_MCP_MAYA_METRICS`` env var
            (``"1"`` → enabled; default disabled).
        job_storage_path: Path to a SQLite database for job persistence.
            ``None`` reads ``DCC_MCP_MAYA_JOB_STORAGE`` env var.  When
            neither is set the server defaults to
            ``<platform_data_dir>/dcc-mcp-maya/jobs.db``.  Set to ``""``
            to disable persistence (in-memory only).
        job_recovery: Recovery policy for interrupted jobs found in the
            storage on startup.  ``"drop"`` (default) discards them;
            ``"requeue"`` re-submits idempotent jobs automatically.
            ``None`` reads ``DCC_MCP_MAYA_JOB_RECOVERY`` env var.
        dcc_pid: Owning Maya process id for ``diagnostics__*`` tools and IPC
            screenshot routing.  Defaults to :func:`os.getpid` (same as
            :class:`~dcc_mcp_core.server_base.DccServerBase`).
        dcc_window_title: Substring to locate the Maya main window (e.g. for
            captures) when no handle is set.  Optional; PID-based lookup
            usually suffices.
        dcc_window_handle: Native window handle (HWND, etc.) when pre-resolved;
            takes precedence over title/PID resolution.
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

        # ── Prometheus metrics (issue #87) ────────────────────────────────────
        effective_metrics = metrics_enabled
        if effective_metrics is None:
            effective_metrics = os.environ.get(_ENV_METRICS, "").strip() == "1"
        if effective_metrics:
            self._config.enable_prometheus = True
            logger.info("[%s] Prometheus /metrics endpoint enabled", "maya")

        # ── Job persistence + notifications (issue #89) ───────────────────────
        effective_job_path = job_storage_path
        if effective_job_path is None:
            effective_job_path = os.environ.get(_ENV_JOB_STORAGE)
        if effective_job_path is None:
            # Default: platform data dir so the DB persists across upgrades.
            try:
                from dcc_mcp_core import get_data_dir  # noqa: PLC0415

                data_dir = Path(get_data_dir()) / "dcc-mcp-maya"
                data_dir.mkdir(parents=True, exist_ok=True)
                effective_job_path = str(data_dir / _DEFAULT_JOB_DB_FILENAME)
            except Exception as exc:
                logger.debug("Could not resolve default job storage path: %s", exc)
        if effective_job_path:
            self._config.job_storage_path = effective_job_path
            logger.info("[%s] Job storage: %s", "maya", effective_job_path)
        elif job_storage_path is not None and not str(job_storage_path).strip():
            # ``""`` means disable persistence; clear path set by :class:`DccServerBase`
            # in ``_init_job_persistence`` (see tests/test_server_job_metrics.py).
            self._config.job_storage_path = ""

        # Job-recovery policy (issue #89).  Stored for use in
        # :meth:`register_builtin_actions` where we can log the effective
        # policy after the server is configured.
        effective_recovery = job_recovery
        if effective_recovery is None:
            effective_recovery = os.environ.get(_ENV_JOB_RECOVERY, "drop").strip().lower()
        self._job_recovery: str = effective_recovery if effective_recovery in ("drop", "requeue") else "drop"
        if self._job_recovery == "requeue":
            logger.info("[%s] Job recovery policy: requeue idempotent interrupted jobs", "maya")

        # Optional :class:`~dcc_mcp_maya.dispatcher.MayaUiDispatcher`
        # attached by the plugin (or by tests). When set, :meth:`stop`
        # drains it before tearing the HTTP server down so any thread
        # blocked inside ``submit_callable`` returns within the normal
        # ``event.wait()`` budget instead of hanging indefinitely
        # (issue #85 / #89).
        self._maya_dispatcher: Any = None

    def attach_dispatcher(self, dispatcher: Any) -> None:
        """Register a :class:`MayaUiDispatcher` (or compatible) for lifecycle integration.

        The server does not create the dispatcher itself because Maya
        needs control over when the :class:`MayaUiPump` is installed
        (that requires a live ``scriptJob``, which only makes sense
        inside a real interactive session). Callers that manage a
        dispatcher should invoke :meth:`attach_dispatcher` after
        :meth:`start` so :meth:`stop` can drain pending jobs.

        Passing ``None`` detaches a previously-registered dispatcher
        and is a no-op when nothing is attached.
        """
        self._maya_dispatcher = dispatcher

    def stop(self) -> None:
        """Stop the HTTP server and drain any attached Maya dispatcher.

        Order matters: we drain the dispatcher **before** the HTTP
        server shuts down so any thread blocked inside
        ``submit_callable`` observes the drained outcome (``Interrupted``)
        and returns before the HTTP handler that originally enqueued
        the job gives up and closes the response.
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
            except Exception as exc:
                logger.warning(
                    "[%s] Error draining Maya dispatcher during stop(): %s",
                    self._dcc_name,
                    exc,
                )
        super().stop()

    # ── Maya-specific overrides ───────────────────────────────────────────────

    def register_builtin_actions(
        self,
        extra_skill_paths: Optional[List[str]] = None,
        include_bundled: bool = True,
        minimal: Optional[bool] = None,
    ) -> "MayaMcpServer":
        """Discover skills, then optionally load only core skills.

        Calls the base-class implementation to scan all skill directories
        so the ``SkillCatalog`` is fully populated (required for
        ``list_skills`` / ``search_skills`` / ``load_skill`` to work).
        Then, depending on the *minimal* flag, either loads a small
        default set of skills or falls back to the legacy "load all"
        behaviour.

        **Minimal mode** (``minimal=True``, the default):

        - Only ``maya-scripting`` and ``maya-scene`` are loaded.
        - Within those skills, only the ``core`` tool-group is active;
          the ``extended`` / ``scene-management`` groups are deactivated
          and appear as ``__group__<name>`` stubs.
        - All other skills remain in ``Discovered`` state and appear as
          ``__skill__<name>`` stubs.
        - The agent can call ``load_skill("maya-primitives")`` to expand
          the surface at any time.

        **Full mode** (``minimal=False``):

        - All bundled skills are loaded with all groups active (legacy).

        Environment variable overrides:

        - ``DCC_MCP_MAYA_MINIMAL=0`` → force full mode.
        - ``DCC_MCP_MAYA_DEFAULT_TOOLS="maya-scripting,maya-scene,..."``
          → customise which skills are loaded at startup.

        Args:
            extra_skill_paths: Additional directories to scan.
            include_bundled: Include dcc-mcp-core bundled skills.
            minimal: If ``True``, only load core skills.  ``None`` reads
                the ``DCC_MCP_MAYA_MINIMAL`` env var (default ``True``).

        Returns:
            ``self`` for chaining.
        """
        # Phase 1: discover all skills (populates SkillCatalog)
        super().register_builtin_actions(
            extra_skill_paths=extra_skill_paths,
            include_bundled=include_bundled,
        )

        # Phase 2: wire in-process executor so skills run inside the live Maya
        # interpreter instead of spawning a subprocess.  This is the correct
        # execution path for any embedded DCC (issue #108).
        self._wire_in_process_executor()

        # Phase 3: resolve minimal mode and load skills selectively
        is_minimal = _resolve_minimal_flag(minimal)
        custom_tools = _resolve_default_tools()

        if not is_minimal:
            # Legacy mode: load all discovered skills
            self._load_all_discovered_skills()
        elif custom_tools is not None:
            # Custom tool list from env var
            self._load_minimal_skills(list(custom_tools.keys()))
        else:
            # Default minimal mode
            self._load_minimal_skills(_MINIMAL_SKILLS)

        # Diagnostic IPC + ``diagnostics__*`` MCP tools are registered in
        # :meth:`DccServerBase.start` with full instance context (pid / window).

        return self

    # ------------------------------------------------------------------
    # In-process executor (issue #108, #122)
    # ------------------------------------------------------------------

    def _wire_in_process_executor(self) -> None:
        """Register the Maya in-process skill executor via register_handler.

        In dcc-mcp-core 0.14.x, ``McpHttpServer.catalog`` returns a plain string
        representation — ``SkillCatalog.set_in_process_executor`` is no longer
        accessible through the server object.  We instead use
        ``McpHttpServer.register_handler`` to wire in-process execution for each
        **currently loaded** action.

        Call this after :meth:`load_skill` / :meth:`register_builtin_actions`
        to cover skills loaded at startup.  Dynamic loads (triggered by the
        ``load_skill`` MCP tool) are handled by the overridden
        :meth:`load_skill` method which calls
        :meth:`_register_inprocess_handlers` automatically.
        """
        try:
            actions = self._server.registry.list_actions_enabled()
        except AttributeError:
            logger.debug("server.registry not available — skipping in-process executor wiring")
            return

        action_names = [a["name"] for a in actions if isinstance(a, dict) and a.get("name")]
        registered = self._register_inprocess_handlers(action_names)
        if registered > 0:
            logger.info("Maya in-process executor: registered %d handler(s) via register_handler", registered)
        else:
            logger.debug("Maya in-process executor: no new handlers registered (no loaded actions found)")

    def _register_inprocess_handlers(self, action_names: List[str]) -> int:
        """Register in-process Python handlers for the given action names.

        For each action that has a ``source_file`` and no handler registered
        yet, wraps :meth:`_execute_in_process` as an
        ``McpHttpServer.register_handler`` callable so that ``tools/call``
        dispatches to the live Maya interpreter instead of spawning a
        ``mayapy`` subprocess.

        Parameters
        ----------
        action_names:
            List of action names returned by ``load_skill`` or discovered via
            ``registry.list_actions_enabled()``.

        Returns
        -------
        int
            Number of handlers newly registered.
        """
        registered = 0
        for action_name in action_names:
            if self._server.has_handler(action_name):
                continue

            try:
                action = self._server.registry.get_action(action_name)
            except Exception:
                continue

            if not action:
                continue

            script_path = action.get("source_file") if isinstance(action, dict) else None
            if not script_path:
                continue

            def _make_handler(spath: str, aname: str):
                def handler(params: dict) -> dict:
                    return self._execute_in_process(spath, params, aname)

                return handler

            try:
                self._server.register_handler(action_name, _make_handler(script_path, action_name))
                registered += 1
            except Exception as exc:
                logger.warning("Failed to register in-process handler for %r: %s", action_name, exc)

        return registered

    def _execute_in_process(self, script_path: str, params: dict, action_name: str) -> dict:
        """Execute a skill script inside the current Maya Python process.

        Routes through the attached :class:`~dcc_mcp_maya.dispatcher.MayaUiDispatcher`
        (if present) so the script runs on Maya's UI thread, which is required
        for any ``maya.cmds`` or ``maya.api`` calls.  Falls back to running
        directly on the calling thread when no dispatcher is attached (standalone
        / ``mayapy`` mode).

        The script must expose ``main(**kwargs) -> dict`` at module level.
        The ``if __name__ == "__main__": run_main(main)`` guard is intentionally
        **not** triggered — we call ``main()`` directly so parameters are
        forwarded without going through a subprocess stdout pipe.

        Parameters
        ----------
        script_path:
            Absolute (or cwd-relative) path to the skill Python script.
        params:
            Keyword arguments to pass to ``main(**params)``.
        action_name:
            Logical action name used as the dispatcher request id and for
            logging.

        Returns
        -------
        dict
            The ``{"success": ..., "message": ..., ...}`` result dict from
            the skill's ``main()`` function.
        """
        dispatcher = self._maya_dispatcher
        if dispatcher is not None and hasattr(dispatcher, "submit_callable"):
            # Route to Maya's UI thread — required for maya.cmds / maya.api.
            result = dispatcher.submit_callable(
                action_name,
                lambda: _run_skill_script(script_path, params),
                affinity="main",
            )
            if isinstance(result, dict):
                output = result.get("output")
                if isinstance(output, dict):
                    return output
                if not result.get("success", True):
                    return {
                        "success": False,
                        "message": result.get("error") or "Dispatcher returned failure for {}".format(action_name),
                    }
                if output is not None:
                    return {"success": True, "message": str(output)}
            return {"success": False, "message": "Dispatcher returned unexpected result for {}".format(action_name)}

        # Standalone / mayapy mode — run directly on the calling thread.
        return _run_skill_script(script_path, params)

    def load_skill(self, skill_name: str) -> bool:
        """Load *skill_name* and register in-process handlers for its actions.

        Extends the base-class implementation so that skills loaded
        dynamically (via the ``load_skill`` MCP tool at runtime) also get
        in-process Python handlers, not just skills loaded during startup via
        :meth:`register_builtin_actions`.

        Returns
        -------
        bool
            ``True`` on success (matches :class:`DccServerBase` return type).
        """
        try:
            action_names: List[str] = self._server.load_skill(skill_name) or []
        except Exception as exc:
            logger.debug("[%s] load_skill(%r) failed: %s", self._dcc_name, skill_name, exc)
            return False

        if action_names:
            newly_registered = self._register_inprocess_handlers(action_names)
            if newly_registered:
                logger.debug(
                    "[%s] load_skill(%r): registered %d in-process handler(s)",
                    self._dcc_name,
                    skill_name,
                    newly_registered,
                )
        return True

    def _load_all_discovered_skills(self) -> None:
        """Load every discovered skill (legacy full-load behaviour)."""
        try:
            skills = self._server.list_skills()
            for skill in skills:
                name = skill.name if hasattr(skill, "name") else skill["name"]
                try:
                    self._server.load_skill(name)
                except Exception as exc:
                    logger.debug("Failed to load skill %r: %s", name, exc)
        except Exception as exc:
            logger.warning("Failed to list skills for full-load: %s", exc)

    def _load_minimal_skills(self, skill_names: List[str]) -> None:
        """Load only the named skills and deactivate non-core groups.

        For each skill in *skill_names*, calls ``load_skill`` and then
        deactivates any groups listed in ``_MINIMAL_DEACTIVATE_GROUPS``
        for that skill.  Other skills stay in ``Discovered`` state.
        """
        registry = self._server.registry
        for name in skill_names:
            try:
                self._server.load_skill(name)
                logger.info("[minimal] Loaded skill %r", name)
            except Exception as exc:
                logger.warning("[minimal] Failed to load skill %r: %s", name, exc)
                continue

            # Deactivate non-core groups for minimal surface
            groups_to_deactivate = _MINIMAL_DEACTIVATE_GROUPS.get(name, [])
            for group_name in groups_to_deactivate:
                try:
                    count = registry.set_group_enabled(group_name, False)
                    logger.info(
                        "[minimal] Deactivated group %r in %r (%d tools collapsed)",
                        group_name,
                        name,
                        count,
                    )
                except Exception as exc:
                    logger.debug(
                        "[minimal] Failed to deactivate group %r in %r: %s",
                        group_name,
                        name,
                        exc,
                    )

    def _version_string(self) -> str:
        """Return the Maya version via ``cmds.about(version=True)``.

        Falls back to ``"unknown"`` when Maya is not running or importable.
        """
        if not _maya_available():
            return "unknown"
        try:
            import maya.cmds as cmds  # noqa: PLC0415

            return str(cmds.about(version=True))
        except Exception:
            return "unknown"

    # ── TransportManager helpers (Maya-specific wrappers) ─────────────────────

    def bind_and_register(
        self,
        transport_manager: Any,
        version: Optional[str] = None,
        metadata: Optional[Any] = None,
    ) -> Any:
        """Register this Maya instance via ``TransportManager.bind_and_register``.

        Auto-detects the Maya version when ``version`` is not supplied.

        Args:
            transport_manager: A :class:`dcc_mcp_core.TransportManager` instance.
            version: Maya version string.  Auto-detected if ``None``.
            metadata: Arbitrary dict stored with the service entry.

        Returns:
            Tuple ``(instance_id, listener)`` or ``None`` on error.
        """
        if version is None:
            version = self._version_string()
        try:
            return transport_manager.bind_and_register(
                "maya",
                version=version,
                metadata=metadata or {},
            )
        except Exception as exc:
            logger.warning("bind_and_register failed: %s", exc)
            return None

    @staticmethod
    def find_best_service(transport_manager: Any, dcc_type: str = "maya") -> Any:
        """Find the best available Maya MCP service.

        Wraps ``TransportManager.find_best_service``.

        Args:
            transport_manager: A :class:`dcc_mcp_core.TransportManager` instance.
            dcc_type: DCC type string to search for.

        Returns:
            Best service instance, or ``None``.
        """
        try:
            return transport_manager.find_best_service(dcc_type)
        except Exception as exc:
            logger.debug("find_best_service failed: %s", exc)
            return None

    @staticmethod
    def rank_services(transport_manager: Any, dcc_type: str = "maya") -> List[Any]:
        """List and rank all active Maya MCP instances.

        Wraps ``TransportManager.rank_services``.

        Args:
            transport_manager: A :class:`dcc_mcp_core.TransportManager` instance.
            dcc_type: DCC type string to filter.

        Returns:
            Ranked list of service info objects.
        """
        try:
            return list(transport_manager.rank_services(dcc_type))
        except Exception as exc:
            logger.debug("rank_services failed: %s", exc)
            return []


# ── module-level singleton helpers ────────────────────────────────────────────
#
# Thin wrapper around :func:`dcc_mcp_core.factory.create_dcc_server`.  The
# singleton holder and lock live at module scope so the Maya plugin
# (``maya/plugin/dcc_mcp_maya_plugin.py``) can reach the live server for
# UI affordances such as gateway-status display, hot-reload toggling, and
# non-blocking restart.

_server_instance: Optional[MayaMcpServer] = None
_server_lock = threading.Lock()
_instance_holder: List[Optional[MayaMcpServer]] = [None]


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

    All keyword arguments accepted by :class:`MayaMcpServer` (``server_name``,
    ``gateway_port``, ``registry_dir``, ``dcc_version``, ``scene``,
    ``enable_gateway_failover``) may be passed through ``**kwargs``.

    Args:
        port: TCP port.  Use ``0`` for a random available port.
        register_builtins: If ``True``, discovers and loads skills.
        extra_skill_paths: Additional directories to scan.
        include_bundled: Include dcc-mcp-core bundled skills.
        enable_hot_reload: Enable skill hot-reload on file changes.
            Also honours ``DCC_MCP_MAYA_HOT_RELOAD=1``.
        minimal: If ``True``, only core skills are loaded at startup.
            ``None`` reads ``DCC_MCP_MAYA_MINIMAL`` env var (default
            ``True``).  Set to ``False`` for legacy full-load behaviour.
        metrics_enabled: Enable the Prometheus ``/metrics`` endpoint.
            Also honours ``DCC_MCP_MAYA_METRICS=1``.
        job_storage_path: SQLite job-persistence file path.
            Also honours ``DCC_MCP_MAYA_JOB_STORAGE``.
        job_recovery: Recovery policy for interrupted jobs: ``"drop"``
            (default) or ``"requeue"``.  Also honours
            ``DCC_MCP_MAYA_JOB_RECOVERY``.
        dcc_pid: Maya process id for diagnostics (see :class:`MayaMcpServer`).
        dcc_window_title: Window title substring for diagnostic capture.
        dcc_window_handle: Pre-resolved native window handle.
        **kwargs: Forwarded to :class:`MayaMcpServer`.

    Returns:
        ``McpServerHandle`` with ``.mcp_url()``, ``.port``, ``.shutdown()``.

    Example::

        import dcc_mcp_maya
        handle = dcc_mcp_maya.start_server(port=8765)
        print(handle.mcp_url())  # http://127.0.0.1:8765/mcp
    """
    global _server_instance

    if dcc_window_title is None:
        w = os.environ.get("DCC_MCP_MAYA_WINDOW_TITLE", "").strip()
        if w:
            dcc_window_title = w

    if register_builtins:
        # Create server instance and call register_builtin_actions with minimal
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
    else:
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
