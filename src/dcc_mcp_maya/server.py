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
