"""MayaMcpServer — embedded MCP Streamable HTTP server for Maya.

Starts a standards-compliant MCP server (2025-03-26 spec) inside Maya using
``dcc-mcp-core``'s ``McpHttpServer``.  All registered actions become MCP
tools that any compatible MCP host (Claude Desktop, OpenClaw, Cursor …) can
call directly.

Skills SOP
----------
Actions are discovered and registered using ``dcc-mcp-core``'s Skills system
rather than traditional manual ``registry.register()`` calls.  The flow is:

1. ``scan_and_load(dcc_name="maya", extra_paths=[...])`` scans every directory
   on the search path for ``SKILL.md`` files.
2. For each discovered ``SkillMetadata``, every script under ``scripts/`` is
   registered as an MCP action with the canonical naming convention::

       {skill_name.replace("-", "_")}__{script_stem}

   e.g.  ``maya_scene__new_scene``, ``maya_primitives__create_sphere``

3. A ``SkillWatcher`` can optionally be attached for hot-reload during
   development (enabled via ``enable_skill_watcher=True``).

Search path resolution (highest → lowest priority):

1. ``DCC_MCP_SKILL_PATHS`` environment variable (colon/semicolon-separated)
2. Built-in skills shipped with this package  (``src/dcc_mcp_maya/skills/``)
3. Platform default  (``dcc_mcp_core.get_skills_dir()``)

Architecture::

    Maya main thread                     Tokio worker thread
    ─────────────────                    ──────────────────────────
    MayaMcpServer.start()   ─────────►  McpHttpServer (axum HTTP)
    _executor.poll_pending() ◄─────────  DccExecutorHandle (mpsc)
        │
        └─► maya.cmds / OpenMaya (main thread safe)

Thread safety
─────────────
``DeferredExecutor`` (from dcc-mcp-core) queues tasks submitted by Tokio
worker threads and runs them synchronously on the Maya main thread when
``poll_pending()`` is called.  Register a repeating ``maya.utils`` callback
to keep the queue drained (see ``_setup_poll_callback``).
"""

# Import future modules
from __future__ import annotations

# Import built-in modules
import importlib
import logging
import threading
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

# Built-in skills directory shipped with this package
_BUILTIN_SKILLS_DIR = Path(__file__).parent / "skills"

# ── lazy imports (Maya not available at test time) ────────────────────────────


def _maya_available() -> bool:
    try:
        import maya.cmds  # noqa: F401

        return True
    except ImportError:
        return False


# ── Skills discovery ──────────────────────────────────────────────────────────


def _collect_skill_search_paths(extra_paths: Optional[List[str]] = None) -> List[str]:
    """Build the ordered skill search path list.

    Priority (highest first):
    1. ``extra_paths`` supplied by the caller
    2. Built-in skills directory (``src/dcc_mcp_maya/skills/``)
    3. ``DCC_MCP_SKILL_PATHS`` env var paths (via ``get_skill_paths_from_env``)
    4. Platform default skills dir (``get_skills_dir()``)
    """
    from dcc_mcp_core import get_skill_paths_from_env, get_skills_dir  # noqa: PLC0415

    paths: List[str] = list(extra_paths or [])

    if _BUILTIN_SKILLS_DIR.is_dir():
        paths.append(str(_BUILTIN_SKILLS_DIR))

    paths.extend(get_skill_paths_from_env())

    default_dir = get_skills_dir()
    if default_dir and default_dir not in paths:
        paths.append(default_dir)

    return paths


def _register_skills(registry, extra_paths: Optional[List[str]] = None) -> Dict[str, int]:
    """Discover skills via ``scan_and_load`` and register them into *registry*.

    Uses the dcc-mcp-core Skills SOP:

    1. ``scan_and_load(dcc_name="maya", extra_paths=[...])``
    2. For each ``SkillMetadata``, register each script as an action using the
       canonical naming: ``{skill_name.replace("-","_")}__{script_stem}``

    Args:
        registry: An ``ActionRegistry`` instance from ``dcc_mcp_core``.
        extra_paths: Additional skill search directories.

    Returns:
        Summary dict ``{skill_name: script_count}`` for observability.
    """
    from dcc_mcp_core import scan_and_load  # noqa: PLC0415

    search_paths = _collect_skill_search_paths(extra_paths)
    skills, skipped = scan_and_load(extra_paths=search_paths, dcc_name="maya")

    if skipped:
        logger.debug("scan_and_load skipped %d path(s): %s", len(skipped), skipped)

    summary: Dict[str, int] = {}
    for skill in skills:
        count = 0
        skill_key = skill.name.replace("-", "_")
        for script_path in skill.scripts:
            stem = Path(script_path).stem
            action_name = f"{skill_key}__{stem}"
            try:
                registry.register(
                    action_name,
                    description=skill.description,
                    category=skill.name,
                    tags=list(skill.tags),
                    dcc="maya",
                    version=str(skill.version) if skill.version else "1.0.0",
                )
                count += 1
            except Exception as exc:
                logger.warning("Failed to register %r from skill %r: %s", action_name, skill.name, exc)

        summary[skill.name] = count
        logger.debug("Registered %d action(s) from skill %r", count, skill.name)

    total = sum(summary.values())
    logger.info("Skills registered: %d actions from %d skill(s)", total, len(summary))
    return summary


def _build_skill_dispatcher(registry, extra_paths: Optional[List[str]] = None):
    """Build an ``ActionDispatcher`` with handlers wired to skill scripts.

    Each skill script is imported as a Python module and its ``main``
    function (if present) is registered as the handler.  This enables
    direct in-process execution — no subprocess overhead.

    Args:
        registry: An ``ActionRegistry`` already populated via ``_register_skills``.
        extra_paths: Same search paths used in ``_register_skills``.

    Returns:
        ``ActionDispatcher`` with all available handlers registered.
    """
    from dcc_mcp_core import ActionDispatcher, scan_and_load  # noqa: PLC0415

    dispatcher = ActionDispatcher(registry)
    search_paths = _collect_skill_search_paths(extra_paths)
    skills, _ = scan_and_load(extra_paths=search_paths, dcc_name="maya")

    for skill in skills:
        skill_key = skill.name.replace("-", "_")
        for script_path in skill.scripts:
            stem = Path(script_path).stem
            action_name = f"{skill_key}__{stem}"
            try:
                spec = importlib.util.spec_from_file_location(action_name, script_path)
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                handler_fn = getattr(mod, "main", None)
                if callable(handler_fn):
                    dispatcher.register_handler(action_name, handler_fn)
                    logger.debug("Registered handler for %r", action_name)
            except Exception as exc:
                logger.warning("Could not load handler for %r: %s", action_name, exc)

    return dispatcher


# ── MayaMcpServer ─────────────────────────────────────────────────────────────


class MayaMcpServer:
    """MCP Streamable HTTP server embedded inside Maya.

    Example::

        server = MayaMcpServer(port=8765)
        server.register_builtin_actions()
        handle = server.start()
        print(handle.mcp_url())    # http://127.0.0.1:8765/mcp
        handle.shutdown()

    Args:
        port: TCP port to listen on.  Use ``0`` for a random available port.
        server_name: Name reported in MCP ``initialize`` response.
        server_version: Version reported in MCP ``initialize`` response.
        enable_main_thread_executor: If ``True`` (default), install a Maya
            event-loop callback to drain the DCC executor queue, enabling
            thread-safe main-thread dispatch for tool handlers.
    """

    def __init__(
        self,
        port: int = 8765,
        server_name: str = "maya-mcp",
        server_version: str = "0.3.0",
        enable_main_thread_executor: bool = True,
    ) -> None:
        from dcc_mcp_core import ActionRegistry, McpHttpConfig, McpHttpServer  # noqa: PLC0415

        self._registry = ActionRegistry()
        self._config = McpHttpConfig(
            port=port,
            server_name=server_name,
            server_version=server_version,
        )
        self._server = McpHttpServer(self._registry, self._config)
        self._handle = None
        self._executor = None
        self._poll_job = None
        self._enable_executor = enable_main_thread_executor and _maya_available()

        if self._enable_executor:
            self._setup_executor()

    # ── executor / main-thread safety ─────────────────────────────────────────

    def _setup_executor(self) -> None:
        """Create the DeferredExecutor for main-thread dispatch."""
        try:
            from dcc_mcp_core._core import DeferredExecutor  # noqa: PLC0415

            self._executor = DeferredExecutor(queue_depth=64)
            logger.debug("DeferredExecutor created (queue_depth=64)")
        except Exception as exc:
            logger.warning("Could not create DeferredExecutor: %s", exc)
            self._executor = None

    def _setup_poll_callback(self) -> None:
        """Register a repeating Maya callback to drain the executor queue."""
        if not self._executor or not _maya_available():
            return
        try:
            import maya.utils  # noqa: PLC0415

            executor = self._executor

            def poll() -> None:
                try:
                    executor.poll_pending()
                except Exception as exc:  # pragma: no cover
                    logger.debug("Executor poll error: %s", exc)

            # executeDeferred reschedules itself — we use a repeating pattern
            def repeating_poll() -> None:
                poll()
                maya.utils.executeDeferred(repeating_poll)

            maya.utils.executeDeferred(repeating_poll)
            logger.debug("Executor poll callback installed via maya.utils.executeDeferred")
        except Exception as exc:
            logger.warning("Could not install poll callback: %s", exc)

    # ── action registration ────────────────────────────────────────────────────

    @property
    def registry(self):
        """The underlying ``ActionRegistry``."""
        return self._registry

    def register_builtin_actions(self, extra_skill_paths: Optional[List[str]] = None) -> "MayaMcpServer":
        """Discover and register all built-in Maya skills into the registry.

        Uses the dcc-mcp-core Skills SOP via ``scan_and_load``:

        1. Scans built-in ``skills/`` directory shipped with this package
        2. Scans ``DCC_MCP_SKILL_PATHS`` environment variable paths
        3. Scans any ``extra_skill_paths`` supplied by the caller

        Action names follow the canonical convention::

            {skill_name.replace("-", "_")}__{script_stem}

        Args:
            extra_skill_paths: Additional directories to scan for SKILL.md files.

        Returns:
            ``self`` for fluent chaining::

                server = MayaMcpServer().register_builtin_actions()
                server = MayaMcpServer().register_builtin_actions(["/my/custom/skills"])
        """
        _register_skills(self._registry, extra_paths=extra_skill_paths)
        return self

    # ── lifecycle ─────────────────────────────────────────────────────────────

    def start(self):
        """Start the MCP HTTP server.

        Returns:
            ``McpServerHandle`` with ``.mcp_url()``, ``.port``, ``.shutdown()``.
        """
        if self._handle is not None:
            logger.warning("MayaMcpServer already running on port %d", self._handle.port)
            return self._handle

        self._handle = self._server.start()
        logger.info("Maya MCP server started at %s", self._handle.mcp_url())

        if self._enable_executor:
            self._setup_poll_callback()

        return self._handle

    def stop(self) -> None:
        """Gracefully stop the server."""
        if self._handle is not None:
            self._handle.shutdown()
            self._handle = None
            logger.info("Maya MCP server stopped")

    @property
    def is_running(self) -> bool:
        """Whether the server is currently running."""
        return self._handle is not None

    @property
    def mcp_url(self) -> Optional[str]:
        """The MCP endpoint URL, or ``None`` if not running."""
        return self._handle.mcp_url() if self._handle else None


# ── module-level singleton helpers ────────────────────────────────────────────

_server_instance: Optional[MayaMcpServer] = None
_lock = threading.Lock()


def start_server(
    port: int = 8765,
    server_name: str = "maya-mcp",
    register_builtins: bool = True,
    extra_skill_paths: Optional[List[str]] = None,
) -> Any:
    """Start (or return the already-running) Maya MCP server.

    Creates a module-level singleton ``MayaMcpServer``, optionally discovers
    and registers all built-in Maya skills, and starts the HTTP server.

    Skills are discovered via the dcc-mcp-core ``scan_and_load`` SOP from:
    - Built-in ``skills/`` directory in this package
    - ``DCC_MCP_SKILL_PATHS`` environment variable
    - ``extra_skill_paths`` argument

    Args:
        port: TCP port.  Use ``0`` for a random available port.
        server_name: Name shown in MCP ``initialize`` response.
        register_builtins: If ``True``, discovers and registers all built-in skills.
        extra_skill_paths: Additional directories to scan for ``SKILL.md`` files.

    Returns:
        ``McpServerHandle`` with ``.mcp_url()``, ``.port``, ``.shutdown()``.

    Example::

        import dcc_mcp_maya
        handle = dcc_mcp_maya.start_server(port=8765)
        print(handle.mcp_url())  # http://127.0.0.1:8765/mcp

        # With custom skill paths:
        handle = dcc_mcp_maya.start_server(extra_skill_paths=["/studio/maya-skills"])
    """
    global _server_instance
    with _lock:
        if _server_instance is None or not _server_instance.is_running:
            _server_instance = MayaMcpServer(
                port=port,
                server_name=server_name,
            )
            if register_builtins:
                _server_instance.register_builtin_actions(extra_skill_paths=extra_skill_paths)
        return _server_instance.start()


def stop_server() -> None:
    """Stop the module-level singleton server."""
    global _server_instance
    with _lock:
        if _server_instance is not None:
            _server_instance.stop()
            _server_instance = None
