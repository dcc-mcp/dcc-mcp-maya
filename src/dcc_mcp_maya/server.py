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


def _maya_available() -> bool:
    """Return True if Maya is importable in this Python environment."""
    try:
        import maya.cmds  # noqa: F401

        return True
    except ImportError:
        return False


class MayaMcpServer(DccServerBase):
    """MCP Streamable HTTP server embedded inside Maya.

    Thin subclass of :class:`~dcc_mcp_core.server_base.DccServerBase`.
    All skill management, hot-reload, gateway election, and lifecycle
    logic is inherited.  This class adds only:

    - Maya builtin skills directory (``skills/``)
    - Maya version detection via ``cmds.about(version=True)``
    - Optional ``register_builtin_actions()`` override that also installs
      IPC diagnostic handlers via
      ``dcc_mcp_core.dcc_server.register_diagnostic_handlers``
    - Maya-specific TransportManager wrappers
      (``bind_and_register``, ``find_best_service``, ``rank_services``)

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
        gateway_port: Port for first-wins gateway competition.  ``None``
            reads ``DCC_MCP_GATEWAY_PORT`` env var; ``0`` disables.
        registry_dir: Directory for the shared ``FileRegistry`` JSON file.
        dcc_version: Maya version string reported to the registry.
        scene: Currently open scene file path reported to the registry.
        enable_gateway_failover: Enable automatic gateway failover election.
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
        )

    # ── Maya-specific overrides ───────────────────────────────────────────────

    def register_builtin_actions(
        self,
        extra_skill_paths: Optional[List[str]] = None,
        include_bundled: bool = True,
    ) -> "MayaMcpServer":
        """Discover skills, then register diagnostic IPC handlers.

        Calls the base-class implementation to scan all skill directories.
        Skill metadata becomes available immediately, while concrete skill
        tools remain progressively loaded by the underlying MCP server.
        This method then registers the standard diagnostic IPC handlers
        (``get_audit_log``, ``get_action_metrics``, ``dispatch_action``) so
        that skill sub-processes can call back into this server.

        Args:
            extra_skill_paths: Additional directories to scan.
            include_bundled: Include dcc-mcp-core bundled skills.

        Returns:
            ``self`` for chaining.
        """
        super().register_builtin_actions(
            extra_skill_paths=extra_skill_paths,
            include_bundled=include_bundled,
        )
        try:
            from dcc_mcp_core.dcc_server import register_diagnostic_handlers  # noqa: PLC0415

            register_diagnostic_handlers(self._server, dcc_name="maya")
        except Exception as exc:
            logger.debug("Failed to register diagnostic handlers: %s", exc)
        return self

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
        register_builtins: If ``True``, discovers and loads all skills.
        extra_skill_paths: Additional directories to scan.
        include_bundled: Include dcc-mcp-core bundled skills.
        enable_hot_reload: Enable skill hot-reload on file changes.
            Also honours ``DCC_MCP_MAYA_HOT_RELOAD=1``.
        **kwargs: Forwarded to :class:`MayaMcpServer`.

    Returns:
        ``McpServerHandle`` with ``.mcp_url()``, ``.port``, ``.shutdown()``.

    Example::

        import dcc_mcp_maya
        handle = dcc_mcp_maya.start_server(port=8765)
        print(handle.mcp_url())  # http://127.0.0.1:8765/mcp
    """
    global _server_instance
    handle = create_dcc_server(
        instance_holder=_instance_holder,
        lock=_server_lock,
        server_class=MayaMcpServer,
        port=port,
        register_builtins=register_builtins,
        extra_skill_paths=extra_skill_paths,
        include_bundled=include_bundled,
        enable_hot_reload=enable_hot_reload,
        hot_reload_env_var="DCC_MCP_MAYA_HOT_RELOAD",
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
