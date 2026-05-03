"""Maya host adapter for dcc-mcp-core 0.14.23 dispatchers."""

# Import future modules
from __future__ import annotations

# Import built-in modules
from typing import Any, Callable, Optional

# Import third-party modules
try:
    from dcc_mcp_core.host import HostAdapter  # noqa: E402
except (ImportError, SyntaxError):  # pragma: no cover - Python 3.7 core host fallback
    HostAdapter = None  # type: ignore[assignment,misc]


if HostAdapter is None:

    class HostAdapter:  # type: ignore[no-redef]
        """Fallback HostAdapter shim for interpreters that cannot load core's host module.

        ``dcc-mcp-core>=0.14.23`` imports :class:`typing.Protocol`, which is only available
        on Python 3.8+.  Maya 2022 ships Python 3.7, so we provide a minimal compatible
        implementation that mirrors the public contract (``start``/``stop``/``run_headless``/
        ``attach_tick``/``detach_tick``) so :class:`MayaHost` remains usable.
        """

        def __init__(
            self,
            dispatcher: Any,
            *,
            tick_interval_active: float = 0.0,
            tick_interval_idle: float = 0.5,
            max_jobs_per_tick: int = 16,
            name: str = "host-adapter",
        ) -> None:
            self._dispatcher = dispatcher
            self._tick_interval_active = tick_interval_active
            self._tick_interval_idle = tick_interval_idle
            self._max_jobs = max_jobs_per_tick
            self._name = name
            self._attached = False

        def start(self) -> None:
            self.attach_tick(lambda: None)
            self._attached = True

        def stop(self, timeout: float = 5.0) -> None:
            _ = timeout
            if self._attached:
                self.detach_tick()
            self._attached = False
            shutdown = getattr(self._dispatcher, "shutdown", None)
            if callable(shutdown):
                shutdown()

        def run_headless(self, stop_event: Any = None) -> None:
            while stop_event is None or not stop_event.is_set():
                tick_blocking = getattr(self._dispatcher, "tick_blocking", None)
                if callable(tick_blocking):
                    tick_blocking(self._max_jobs, 50)
                else:
                    break

        @property
        def is_running(self) -> bool:
            return self._attached

        def is_background(self) -> bool:
            return True

        def attach_tick(self, tick_fn: Callable[[], Optional[float]]) -> None:
            raise NotImplementedError

        def detach_tick(self) -> None:
            raise NotImplementedError


_CALL_METADATA_KEYS = {
    "affinity",
    "context",
    "action_name",
    "skill_name",
    "execution",
    "timeout_hint_secs",
}


class MayaCallableDispatcher:
    """Callable bridge used after native core dispatcher attachment.

    ``McpHttpServer.attach_dispatcher`` owns the actual Queue/BlockingDispatcher
    hop in core 0.14.23.  This bridge only prevents the Python in-process
    executor from falling back to subprocess execution; the callable is already
    running on the host-dispatched thread when it reaches this point.
    """

    def __init__(self, dispatcher: Any) -> None:
        self._dispatcher = dispatcher

    def dispatch_callable(self, func: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        call_kwargs = {k: v for k, v in kwargs.items() if k not in _CALL_METADATA_KEYS}
        return func(*args, **call_kwargs)

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
