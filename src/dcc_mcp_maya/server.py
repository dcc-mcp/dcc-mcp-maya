"""MayaMcpServer — embedded MCP Streamable HTTP server for Maya.

Starts a standards-compliant MCP server (2025-03-26 spec) inside Maya using
``dcc-mcp-core``'s ``McpHttpServer``.  All registered actions become MCP
tools that any compatible MCP host (Claude Desktop, OpenClaw, Cursor …) can
call directly.

Skills-First API (v0.12.12+)
-----------------------------
The preferred entry point is :func:`create_skill_manager` from ``dcc-mcp-core``,
which wires up ``ActionRegistry``, ``ActionDispatcher``, ``SkillCatalog`` and
auto-discovers skills from env vars in one call.

:class:`MayaMcpServer` wraps this factory and adds Maya-specific path discovery
so built-in skills shipped with this package are always included.

Flow::

    server = MayaMcpServer(port=8765)
    server.register_builtin_actions()   # discover & load all skills
    handle = server.start()
    print(handle.mcp_url())             # http://127.0.0.1:8765/mcp
    handle.shutdown()

Or via the module-level singleton helper::

    import dcc_mcp_maya
    handle = dcc_mcp_maya.start_server(port=8765)
    print(handle.mcp_url())

Action naming convention (unchanged)::

    {skill_name.replace("-", "_")}__{script_stem}
    # e.g. maya_scene__new_scene, maya_primitives__create_sphere

Search path resolution (highest → lowest priority):

1. ``extra_skill_paths`` supplied by the caller
2. Built-in skills shipped with this package  (``src/dcc_mcp_maya/skills/``)
3. ``DCC_MCP_MAYA_SKILL_PATHS`` environment variable (Maya-specific, v0.12.12+)
4. ``DCC_MCP_SKILL_PATHS`` environment variable (global fallback)
5. Platform default  (``dcc_mcp_core.get_skills_dir()``)

Architecture::

    Maya main thread                     Tokio worker thread
    ─────────────────                    ──────────────────────────
    MayaMcpServer.start()   ─────────►  McpHttpServer (axum HTTP)
                                         handlers called via registry
"""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging
import threading
from pathlib import Path
from typing import Any, List, Optional

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


# ── Skills search path helpers ────────────────────────────────────────────────


def _collect_skill_search_paths(extra_paths: Optional[List[str]] = None) -> List[str]:
    """Build the ordered skill search path list.

    Priority (highest first):
    1. ``extra_paths`` supplied by the caller
    2. Built-in skills directory (``src/dcc_mcp_maya/skills/``)
    3. ``DCC_MCP_MAYA_SKILL_PATHS`` — Maya-specific env var (v0.12.12+)
    4. ``DCC_MCP_SKILL_PATHS`` — global fallback env var
    5. Platform default skills dir (``get_skills_dir()``)
    """
    from dcc_mcp_core import get_app_skill_paths_from_env, get_skill_paths_from_env, get_skills_dir  # noqa: PLC0415

    paths: List[str] = list(extra_paths or [])

    if _BUILTIN_SKILLS_DIR.is_dir():
        paths.append(str(_BUILTIN_SKILLS_DIR))

    # Per-app env var: DCC_MCP_MAYA_SKILL_PATHS (highest priority among env vars)
    paths.extend(get_app_skill_paths_from_env("maya"))

    # Global fallback env var: DCC_MCP_SKILL_PATHS
    paths.extend(get_skill_paths_from_env())

    default_dir = get_skills_dir()
    if default_dir and default_dir not in paths:
        paths.append(default_dir)

    return paths


# ── MayaMcpServer ─────────────────────────────────────────────────────────────


class MayaMcpServer:
    """MCP Streamable HTTP server embedded inside Maya.

    Uses the Skills-First API introduced in dcc-mcp-core v0.12.12:
    :func:`dcc_mcp_core.create_skill_manager` wires up the full stack
    (registry, dispatcher, catalog) in one call.

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
    """

    def __init__(
        self,
        port: int = 8765,
        server_name: str = "maya-mcp",
        server_version: str = "0.3.0",
    ) -> None:
        from dcc_mcp_core import McpHttpConfig, create_skill_manager  # noqa: PLC0415

        self._config = McpHttpConfig(
            port=port,
            server_name=server_name,
            server_version=server_version,
        )
        # create_skill_manager pre-wires ActionRegistry + ActionDispatcher + SkillCatalog
        # and auto-discovers skills from env vars (DCC_MCP_MAYA_SKILL_PATHS, DCC_MCP_SKILL_PATHS)
        self._server = create_skill_manager("maya", self._config)
        self._handle = None

    # ── action registration ────────────────────────────────────────────────────

    @property
    def registry(self):
        """The underlying ``ActionRegistry``.

        .. deprecated::
            With ``create_skill_manager`` (v0.12.12+), the registry is managed
            internally by the ``McpHttpServer``.  Use ``self._server.list_skills()``
            or the HTTP ``tools/list`` endpoint to inspect registered tools.
        """
        return getattr(self._server, "_registry", None)

    def register_builtin_actions(self, extra_skill_paths: Optional[List[str]] = None) -> "MayaMcpServer":
        """Discover and load all built-in Maya skills into the server.

        Uses the dcc-mcp-core SkillCatalog API (v0.12.12+):

        1. ``server.discover(extra_paths, dcc_name="maya")`` — scans all paths
           for ``SKILL.md`` files and caches skill metadata.
        2. ``server.load_skill(name)`` — registers each script as an MCP action
           with the canonical naming convention::

               {skill_name.replace("-", "_")}__{script_stem}

        Skills are discovered from (highest → lowest priority):

        - ``extra_skill_paths`` supplied by the caller
        - Built-in ``skills/`` directory shipped with this package
        - ``DCC_MCP_MAYA_SKILL_PATHS`` environment variable (Maya-specific)
        - ``DCC_MCP_SKILL_PATHS`` environment variable (global fallback)
        - Platform default skills directory

        Args:
            extra_skill_paths: Additional directories to scan for SKILL.md files.

        Returns:
            ``self`` for fluent chaining::

                server = MayaMcpServer().register_builtin_actions()
                server = MayaMcpServer().register_builtin_actions(["/my/custom/skills"])
        """
        search_paths = _collect_skill_search_paths(extra_skill_paths)

        count = self._server.discover(extra_paths=search_paths, dcc_name="maya")
        logger.debug("SkillCatalog discovered %d skill(s)", count)

        loaded = 0
        failed = 0
        for summary in self._server.list_skills():
            skill_name = summary.name if hasattr(summary, "name") else summary["name"]
            try:
                self._server.load_skill(skill_name)
                loaded += 1
            except Exception as exc:
                logger.warning("Failed to load skill %r: %s", skill_name, exc)
                failed += 1

        logger.info(
            "Skills loaded: %d loaded, %d failed (from %d discovered)",
            loaded,
            failed,
            count,
        )

        # Register diagnostic IPC handlers and set DCC_MCP_IPC_ADDRESS so that
        # skill subprocesses (dcc-diagnostics, workflow) can call back into this
        # server to retrieve live audit log, metrics, and dispatch relays.
        from dcc_mcp_maya.diagnostics import register_diagnostic_handlers  # noqa: PLC0415

        register_diagnostic_handlers(self._server)
        return self

    # ── skill discovery helpers ───────────────────────────────────────────────

    def search_skills(
        self,
        category: Optional[str] = None,
        tags: Optional[List[str]] = None,
        dcc_name: Optional[str] = None,
    ) -> List[Any]:
        """Search registered skills / actions using dcc-mcp-core's ``search_actions``.

        Wraps ``ActionRegistry.search_actions`` (v0.12.5+).  All filters are
        applied as AND conditions; passing ``None`` ignores that filter.

        Args:
            category: Filter by action category (e.g. ``"geometry"``).
            tags: Filter by tag list (e.g. ``["mesh", "create"]``).
            dcc_name: Filter by DCC name (e.g. ``"maya"``).  Defaults to
                ``"maya"`` when not specified.

        Returns:
            List of :class:`ActionInfo` objects (or dicts) matching the filters.

        Example::

            server.register_builtin_actions()
            results = server.search_skills(category="geometry", tags=["create"])
        """
        registry = self.registry
        if registry is None:
            logger.warning("Registry not available; returning empty search result")
            return []

        effective_dcc = dcc_name if dcc_name is not None else "maya"
        try:
            return list(
                registry.search_actions(
                    category=category,
                    tags=tags,
                    dcc_name=effective_dcc,
                )
            )
        except Exception as exc:
            logger.debug("search_actions failed: %s", exc)
            return []

    def get_skill_categories(self) -> List[str]:
        """Return all unique action categories registered in the server.

        Wraps ``ActionRegistry.get_categories`` (v0.12.5+).

        Returns:
            Sorted list of category strings.
        """
        registry = self.registry
        if registry is None:
            return []
        try:
            return list(registry.get_categories())
        except Exception as exc:
            logger.debug("get_categories failed: %s", exc)
            return []

    def get_skill_tags(self, dcc_name: Optional[str] = None) -> List[str]:
        """Return all unique tags for the given DCC (or all DCCs).

        Wraps ``ActionRegistry.get_tags`` (v0.12.5+).

        Args:
            dcc_name: If given, only return tags for that DCC.  Defaults to
                ``"maya"`` when not specified.

        Returns:
            Sorted list of tag strings.
        """
        registry = self.registry
        if registry is None:
            return []
        effective_dcc = dcc_name if dcc_name is not None else "maya"
        try:
            return list(registry.get_tags(dcc_name=effective_dcc))
        except Exception as exc:
            logger.debug("get_tags failed: %s", exc)
            return []

    def unregister_skill(self, name: str, dcc_name: Optional[str] = None) -> None:
        """Unregister a skill / action from the server's registry.

        Wraps ``ActionRegistry.unregister`` (v0.12.6+).  Silently ignores
        errors so callers do not need to guard against missing entries.

        Args:
            name: The canonical action name (e.g.
                ``"maya_scene__create_object"``).
            dcc_name: If given, only unregister for that DCC.  If ``None``,
                unregisters globally (all DCCs).

        Example::

            server.unregister_skill("maya_scene__create_object")
            server.unregister_skill("maya_scene__create_object", dcc_name="maya")
        """
        registry = self.registry
        if registry is None:
            logger.warning("Registry not available; cannot unregister skill %r", name)
            return
        try:
            registry.unregister(name, dcc_name=dcc_name)
            logger.debug("Unregistered skill %r (dcc=%r)", name, dcc_name)
        except Exception as exc:
            logger.debug("unregister(%r) failed: %s", name, exc)

    def find_skills(
        self,
        query: Optional[str] = None,
        tags: Optional[List[str]] = None,
        dcc: Optional[str] = None,
    ) -> List[Any]:
        """Search the SkillCatalog using ``SkillCatalog.find_skills`` (v0.12.12+).

        Matches on skill name, description, ``search_hint``, and tool names.
        All filters are applied as AND conditions; ``None`` ignores that filter.

        Args:
            query: Free-text search term matched against name/description/hint.
            tags: List of tags that the skill must have **all** of.
            dcc: If given, restrict results to skills targeting this DCC (e.g.
                ``"maya"``).

        Returns:
            List of :class:`SkillSummary` objects (or dicts) matching the
            query.  Returns ``[]`` when the catalog is unavailable or on error.

        Example::

            server.register_builtin_actions()
            hits = server.find_skills(query="bounding box")
            hits = server.find_skills(tags=["rigging"], dcc="maya")
        """
        try:
            return list(self._server.find_skills(query=query, tags=tags, dcc=dcc))
        except Exception as exc:
            logger.debug("find_skills failed: %s", exc)
            return []

    def is_skill_loaded(self, name: str) -> bool:
        """Check whether a skill has been loaded into the SkillCatalog.

        Wraps ``SkillCatalog.is_loaded`` (v0.12.12+).

        Args:
            name: Skill name as discovered (e.g. ``"maya-scene"``).

        Returns:
            ``True`` if the skill is currently loaded, ``False`` otherwise.

        Example::

            server.register_builtin_actions()
            if server.is_skill_loaded("maya-scene"):
                print("maya-scene is ready")
        """
        try:
            return bool(self._server.is_loaded(name))
        except Exception as exc:
            logger.debug("is_loaded(%r) failed: %s", name, exc)
            return False

    def get_skill_info(self, name: str) -> Any:
        """Return full metadata for a skill from the SkillCatalog.

        Wraps ``SkillCatalog.get_skill_info`` (v0.12.12+).

        Args:
            name: Skill name as discovered (e.g. ``"maya-scene"``).

        Returns:
            :class:`SkillMetadata` instance (or dict), or ``None`` if the skill
            is not found or the catalog is unavailable.

        Example::

            info = server.get_skill_info("maya-scene")
            if info:
                print(info.description)
        """
        try:
            return self._server.get_skill_info(name)
        except Exception as exc:
            logger.debug("get_skill_info(%r) failed: %s", name, exc)
            return None

    # ── TransportManager helpers ──────────────────────────────────────────────

    def bind_and_register(
        self,
        transport_manager: Any,
        version: Optional[str] = None,
        metadata: Optional[Any] = None,
    ) -> Any:
        """Register this Maya instance via ``TransportManager.bind_and_register``.

        One-shot helper that auto-selects the best transport (Named Pipe on
        Windows, Unix Socket on Linux/macOS, TCP fallback) and registers the
        service so other processes can discover it via ``find_best_service`` /
        ``rank_services``.

        Wraps ``TransportManager.bind_and_register`` (v0.12+).

        Args:
            transport_manager: A :class:`dcc_mcp_core.TransportManager`
                instance managing service discovery.
            version: Maya version string reported to the registry (e.g.
                ``"2025"``).  If ``None``, attempts to read ``cmds.about(v=True)``.
            metadata: Arbitrary dict stored with the service entry (e.g.
                ``{"artist": "user1"}``).

        Returns:
            Tuple ``(instance_id, listener)`` returned by
            ``TransportManager.bind_and_register``, or ``None`` on error.

        Example::

            from dcc_mcp_core import TransportManager
            mgr = TransportManager()
            instance_id, listener = server.bind_and_register(mgr, version="2025")
        """
        if version is None:
            try:
                import maya.cmds as cmds  # noqa: PLC0415

                version = str(cmds.about(version=True))
            except Exception:
                version = "unknown"

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
        """Find the best available Maya service via ``TransportManager.find_best_service``.

        Wraps ``TransportManager.find_best_service`` (v0.12+).

        Args:
            transport_manager: A :class:`dcc_mcp_core.TransportManager`
                instance managing service discovery.
            dcc_type: DCC type string to search for.  Defaults to ``"maya"``.

        Returns:
            The best service instance, or ``None`` if none are available.

        Example::

            from dcc_mcp_core import TransportManager
            mgr = TransportManager()
            service = MayaMcpServer.find_best_service(mgr)
        """
        try:
            return transport_manager.find_best_service(dcc_type)
        except Exception as exc:
            logger.debug("find_best_service failed: %s", exc)
            return None

    @staticmethod
    def rank_services(transport_manager: Any, dcc_type: str = "maya") -> List[Any]:
        """List and rank all active Maya instances via ``TransportManager.rank_services``.

        Services are ordered by: local IPC available → local IPC busy →
        local TCP available → remote TCP.

        Wraps ``TransportManager.rank_services`` (v0.12+).

        Args:
            transport_manager: A :class:`dcc_mcp_core.TransportManager`
                instance managing service discovery.
            dcc_type: DCC type string to filter.  Defaults to ``"maya"``.

        Returns:
            Ranked list of service info objects.  Returns ``[]`` on error.

        Example::

            from dcc_mcp_core import TransportManager
            mgr = TransportManager()
            services = MayaMcpServer.rank_services(mgr)
            # [service_local_ipc, service_busy_ipc, service_tcp, ...]
        """
        try:
            return list(transport_manager.rank_services(dcc_type))
        except Exception as exc:
            logger.debug("rank_services failed: %s", exc)
            return []

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

    def get_capabilities(self) -> Any:
        """Return the Maya DCC capabilities as a ``DccCapabilities`` instance.

        Declares the feature set supported by this Maya integration for
        cross-DCC protocol negotiation (v0.12.7+).

        Returns:
            ``dcc_mcp_core.DccCapabilities`` instance with Maya-specific flags.

        Example::

            caps = server.get_capabilities()
            print(caps.transform)    # True
            print(caps.to_dict())    # serialisable dict
        """
        from dcc_mcp_maya.capabilities import maya_capabilities  # noqa: PLC0415

        return maya_capabilities()


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

    Creates a module-level singleton :class:`MayaMcpServer`, optionally discovers
    and loads all built-in Maya skills, and starts the HTTP server.

    Uses the dcc-mcp-core Skills-First API (``create_skill_manager``, v0.12.12+).
    Skills are discovered from:

    - Built-in ``skills/`` directory in this package
    - ``DCC_MCP_MAYA_SKILL_PATHS`` environment variable (Maya-specific, v0.12.12+)
    - ``DCC_MCP_SKILL_PATHS`` environment variable (global fallback)
    - ``extra_skill_paths`` argument

    Args:
        port: TCP port.  Use ``0`` for a random available port.
        server_name: Name shown in MCP ``initialize`` response.
        register_builtins: If ``True``, discovers and loads all built-in skills.
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
