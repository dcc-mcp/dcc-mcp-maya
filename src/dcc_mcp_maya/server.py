"""MayaMcpServer — embedded MCP Streamable HTTP server for Maya.

Starts a standards-compliant MCP server (2025-03-26 spec) inside Maya using
``dcc-mcp-core``'s ``McpHttpServer``.  All registered actions become MCP
tools that any compatible MCP host (Claude Desktop, OpenClaw, Cursor …) can
call directly.

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
import logging
import threading
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

# ── lazy imports (Maya not available at test time) ────────────────────────────


def _maya_available() -> bool:
    try:
        import maya.cmds  # noqa: F401

        return True
    except ImportError:
        return False


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
        server_version: str = "0.2.0",
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

    def register_builtin_actions(self) -> MayaMcpServer:
        """Register all built-in Maya actions into the registry.

        Returns self for chaining::

            server = MayaMcpServer().register_builtin_actions()
        """
        from dcc_mcp_maya.actions import register_all  # noqa: PLC0415

        register_all(self._registry)
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
    def mcp_url(self) -> str | None:
        """The MCP endpoint URL, or ``None`` if not running."""
        return self._handle.mcp_url() if self._handle else None


# ── module-level singleton helpers ────────────────────────────────────────────

_server_instance: MayaMcpServer | None = None
_lock = threading.Lock()


def start_server(
    port: int = 8765,
    server_name: str = "maya-mcp",
    register_builtins: bool = True,
) -> Any:
    """Start (or return the already-running) Maya MCP server.

    Creates a module-level singleton ``MayaMcpServer``, optionally registers
    built-in Maya actions, and starts the HTTP server.

    Args:
        port: TCP port.  Use ``0`` for a random available port.
        server_name: Name shown in MCP ``initialize`` response.
        register_builtins: If ``True``, registers all built-in Maya actions.

    Returns:
        ``McpServerHandle`` with ``.mcp_url()``, ``.port``, ``.shutdown()``.

    Example::

        import dcc_mcp_maya
        handle = dcc_mcp_maya.start_server(port=8765)
        print(handle.mcp_url())  # http://127.0.0.1:8765/mcp
    """
    global _server_instance
    with _lock:
        if _server_instance is None or not _server_instance.is_running:
            _server_instance = MayaMcpServer(
                port=port,
                server_name=server_name,
            )
            if register_builtins:
                _server_instance.register_builtin_actions()
        return _server_instance.start()


def stop_server() -> None:
    """Stop the module-level singleton server."""
    global _server_instance
    with _lock:
        if _server_instance is not None:
            _server_instance.stop()
            _server_instance = None
