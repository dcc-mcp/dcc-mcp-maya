"""Host-dispatcher resolution for the Maya plugin bootstrap.

The plugin historically wired ``dcc_mcp_core.host.BlockingDispatcher`` /
``QueueDispatcher`` directly. On some ``dcc-mcp-core`` builds (missing or
partial Rust extension) those symbols import as ``None``, which crashes
plugin startup with ``TypeError: 'NoneType' object is not callable``.

This module tries the core Rust dispatchers first and falls back to the
Python-side :class:`~dcc_mcp_maya.dispatcher.MayaUiDispatcher` /
:class:`~dcc_mcp_maya.dispatcher.MayaStandaloneDispatcher` path that
``MayaMcpServer`` already uses for direct ``start_server()`` calls.
"""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging
from dataclasses import dataclass
from typing import Any, Optional, Tuple, Type

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class PluginHostStartup:
    """Resolved dispatcher wiring for plugin / bootstrap startup."""

    dispatcher: Any
    host: Any = None
    ui_pump: Any = None
    backend: str = "unknown"


class PluginDispatcherError(RuntimeError):
    """Raised when no host dispatcher can be constructed."""

    def __init__(
        self,
        message: str,
        *,
        core_version: str,
        is_batch: bool,
        core_error: str = "",
        fallback_error: str = "",
    ) -> None:
        super().__init__(message)
        self.core_version = core_version
        self.is_batch = is_batch
        self.core_error = core_error
        self.fallback_error = fallback_error

    def as_dict(self) -> dict:
        mode = "batch" if self.is_batch else "interactive"
        remedies = [
            "Verify dcc-mcp-core is installed for this Maya Python: `mayapy -m pip show dcc-mcp-core`",
            "Reinstall a wheel that includes the native extension for your Maya "
            "Python version (see dcc-mcp-maya README / pyproject pins).",
            "If the native extension is intentionally unavailable, use a "
            "dcc-mcp-maya build that includes the Python dispatcher fallback "
            "(resolve_plugin_host_startup).",
        ]
        return {
            "success": False,
            "message": str(self),
            "error": "dispatcher-unavailable",
            "context": {
                "core_version": self.core_version,
                "mode": mode,
                "core_error": self.core_error or None,
                "fallback_error": self.fallback_error or None,
                "possible_solutions": remedies,
            },
        }


def _resolve_core_version() -> str:
    try:
        import dcc_mcp_core  # noqa: PLC0415

        return str(getattr(dcc_mcp_core, "__version__", "unknown"))
    except Exception:  # noqa: BLE001
        return "unknown"


def _try_core_host_dispatcher(is_batch: bool) -> Tuple[Optional[Any], str]:
    """Instantiate a core Rust dispatcher when the symbol is callable."""
    try:
        from dcc_mcp_core.host import BlockingDispatcher, QueueDispatcher  # noqa: PLC0415
    except Exception as exc:  # noqa: BLE001
        return None, "import dcc_mcp_core.host failed: {}".format(exc)

    factory: Optional[Type[Any]]
    label: str
    if is_batch:
        factory = BlockingDispatcher
        label = "BlockingDispatcher"
    else:
        factory = QueueDispatcher
        label = "QueueDispatcher"

    if factory is None:
        return None, "{} is None (native core dispatcher unavailable)".format(label)
    if not callable(factory):
        return None, "{} is not callable (got {!r})".format(label, factory)

    try:
        return factory(), ""
    except Exception as exc:  # noqa: BLE001
        return None, "{}() raised: {}".format(label, exc)


def _try_python_host_dispatcher(is_batch: bool) -> Tuple[Optional[Any], Optional[Any], str]:
    """Fallback to the Python-side Maya dispatchers."""
    try:
        from dcc_mcp_maya.dispatcher import create_dispatcher  # noqa: PLC0415
    except Exception as exc:  # noqa: BLE001
        return None, None, "import create_dispatcher failed: {}".format(exc)

    try:
        dispatcher, ui_pump = create_dispatcher()
    except Exception as exc:  # noqa: BLE001
        return None, None, "create_dispatcher() raised: {}".format(exc)

    if dispatcher is None:
        return None, None, "create_dispatcher() returned None dispatcher"

    if is_batch:
        expected = "MayaStandaloneDispatcher"
        actual = type(dispatcher).__name__
        if actual != expected:
            return None, None, "expected {}, got {}".format(expected, actual)
        return dispatcher, None, ""

    expected = "MayaUiDispatcher"
    actual = type(dispatcher).__name__
    if actual != expected:
        return None, None, "expected {}, got {}".format(expected, actual)
    if ui_pump is None:
        return None, None, "interactive mode requires MayaUiPump"
    return dispatcher, ui_pump, ""


def resolve_plugin_host_startup(is_batch: bool) -> PluginHostStartup:
    """Resolve dispatcher wiring for plugin startup.

    Parameters
    ----------
    is_batch:
        ``True`` when ``cmds.about(batch=True)`` (mayapy / batch mode).

    Returns
    -------
    PluginHostStartup
        Tuple-like bundle: ``dispatcher`` is always set; ``host`` is set
        only for core Rust dispatchers; ``ui_pump`` is set for the Python
        interactive fallback path (and installed by the caller).
    """
    core_dispatcher, core_error = _try_core_host_dispatcher(is_batch)
    if core_dispatcher is not None:
        from dcc_mcp_maya.host import MayaHost  # noqa: PLC0415

        logger.debug(
            "plugin host dispatcher: core %s",
            "BlockingDispatcher" if is_batch else "QueueDispatcher",
        )
        return PluginHostStartup(
            dispatcher=core_dispatcher,
            host=MayaHost(core_dispatcher),
            ui_pump=None,
            backend="core-rust",
        )

    fallback_dispatcher, ui_pump, fallback_error = _try_python_host_dispatcher(is_batch)
    if fallback_dispatcher is not None:
        logger.warning(
            "Core host dispatcher unavailable (%s); falling back to Python %s",
            core_error or "unknown",
            type(fallback_dispatcher).__name__,
        )
        return PluginHostStartup(
            dispatcher=fallback_dispatcher,
            host=None,
            ui_pump=ui_pump,
            backend="python-fallback",
        )

    core_version = _resolve_core_version()
    mode = "batch" if is_batch else "interactive"
    message = "Cannot start MCP server: no host dispatcher available for {} mode (dcc-mcp-core {}).".format(
        mode, core_version
    )
    raise PluginDispatcherError(
        message,
        core_version=core_version,
        is_batch=is_batch,
        core_error=core_error,
        fallback_error=fallback_error,
    )


def install_plugin_host_startup(startup: PluginHostStartup) -> None:
    """Install pump hooks for the resolved startup bundle."""
    if startup.ui_pump is not None:
        startup.ui_pump.install()


def shutdown_plugin_host_startup(startup: Optional[PluginHostStartup]) -> None:
    """Tear down pump / host hooks created by :func:`resolve_plugin_host_startup`."""
    if startup is None:
        return
    if startup.ui_pump is not None:
        try:
            startup.ui_pump.uninstall()
        except Exception as exc:  # noqa: BLE001
            logger.debug("ui pump uninstall skipped: %s", exc)
    if startup.host is not None:
        try:
            startup.host.stop()
        except Exception as exc:  # noqa: BLE001
            logger.debug("MayaHost stop skipped: %s", exc)
