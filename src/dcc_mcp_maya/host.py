"""Maya host adapter for dcc-mcp-core host dispatchers."""

# Import future modules
from __future__ import annotations

# Import built-in modules
from typing import Any, Callable, Optional

# Import third-party modules
from dcc_mcp_core.host import HostAdapter


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
    """Drive a core host dispatcher from Maya's native idle loop."""

    def __init__(self, dispatcher: Any, **kwargs: Any) -> None:
        kwargs.setdefault("name", "maya-host")
        super().__init__(dispatcher, **kwargs)
        self._script_job: Optional[int] = None

    def is_background(self) -> bool:
        try:
            import maya.cmds as cmds  # noqa: PLC0415

            return bool(cmds.about(batch=True))
        except ImportError:
            return True

    def attach_tick(self, tick_fn: Callable[[], Optional[float]]) -> None:
        import maya.cmds as cmds  # noqa: PLC0415

        if self._script_job is not None:
            return
        self._script_job = cmds.scriptJob(idleEvent=lambda: tick_fn(), protected=True)

    def detach_tick(self) -> None:
        if self._script_job is None:
            return
        try:
            import maya.cmds as cmds  # noqa: PLC0415

            if cmds.scriptJob(exists=self._script_job):
                cmds.scriptJob(kill=self._script_job)
        finally:
            self._script_job = None
