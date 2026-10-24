"""Maya host adapter for dcc-mcp-core host dispatchers."""

# Import future modules
from __future__ import annotations

# Import built-in modules
from typing import Any, Callable, Optional

# Import third-party modules
from dcc_mcp_core.host import HostAdapter

from dcc_mcp_maya.api import require_main_thread


class MayaCallableDispatcher:
    """Callable bridge used after native core dispatcher attachment.

    ``McpHttpServer.attach_dispatcher`` owns the native dispatcher hop.
    This bridge lets ``HostExecutionBridge`` share that same route for
    in-process skill execution; the callable is already running on the
    host-dispatched thread when it reaches this point.
    """

    def __init__(self, dispatcher: Any) -> None:
        self._dispatcher = dispatcher

    def dispatch_callable(self, func: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        return func(*args, **kwargs)

    def shutdown(self, reason: str = "Interrupted") -> Any:
        _ = reason
        return self._dispatcher.shutdown()


class MayaHost(HostAdapter):
    """Drive a core host dispatcher from Maya's Qt main loop."""

    def __init__(self, dispatcher: Any, **kwargs: Any) -> None:
        kwargs.setdefault("name", "maya-host")
        super().__init__(dispatcher, **kwargs)
        self._tick_timer: Optional[Any] = None

    @require_main_thread
    def is_background(self) -> bool:
        try:
            import maya.cmds as cmds  # noqa: PLC0415

            return bool(cmds.about(batch=True))
        except ImportError:
            return True

    @require_main_thread
    def attach_tick(self, tick_fn: Callable[[], Optional[float]]) -> None:
        if self._tick_timer is not None:
            return
        app = None
        for binding in ("PySide6", "PySide2"):
            try:
                if binding == "PySide6":
                    from PySide6.QtCore import QCoreApplication, QTimer  # noqa: PLC0415
                else:
                    from PySide2.QtCore import QCoreApplication, QTimer  # noqa: PLC0415
            except ImportError:
                continue
            app = QCoreApplication.instance()
            if app is not None:
                break
        if app is None:
            raise RuntimeError("MayaHost requires a running Qt application")
        timer = QTimer(app)
        timer.setSingleShot(True)

        @require_main_thread
        def run_tick() -> None:
            # A queued timeout from a retired timer must not revive dispatch.
            if self._tick_timer is not timer:
                return
            try:
                interval = tick_fn()
            except Exception:
                if self._tick_timer is timer:
                    self.detach_tick()
                raise
            if self._tick_timer is not timer:
                return
            if interval is None:
                self.detach_tick()
            else:
                timer.start(max(0, int(interval * 1000)))

        timer.timeout.connect(run_tick)
        self._tick_timer = timer
        timer.start(0)

    @require_main_thread
    def detach_tick(self) -> None:
        timer = self._tick_timer
        self._tick_timer = None
        if timer is not None:
            try:
                timer.stop()
            finally:
                timer.deleteLater()
