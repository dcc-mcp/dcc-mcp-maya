"""Standalone (mayapy / batch) dispatcher.

Synchronous dispatcher used outside the interactive Maya event loop:
``mayapy`` scripts, ``Render.exe``, ``maya -batch``.  No queue, no
threads, no main-thread distinction.

See: https://github.com/loonghao/dcc-mcp-maya/issues/128
"""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging
import threading
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)

_STANDALONE_MAYA_LOCK = threading.RLock()


class MayaStandaloneDispatcher:
    """Dispatcher for ``mayapy`` / batch-render contexts.

    All jobs execute directly on the calling thread — there is no event
    loop, no idle callbacks, and no notion of a "main thread" distinct from
    the caller.  This is the right choice for:

    - ``mayapy`` standalone scripts
    - ``Render.exe`` contexts
    - ``maya -batch`` mode
    """

    def __init__(self) -> None:
        # Even without a UI event loop, Maya's Python API is process-global
        # and not safe to enter concurrently from HTTP worker threads.  The
        # lock is intentionally shared by every dispatcher instance in this
        # process because multi-server standalone runs still share one Maya.
        self._lock = _STANDALONE_MAYA_LOCK

    def submit(
        self,
        action_name: str,
        payload: Optional[str] = None,
        affinity: str = "any",
        timeout_ms: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Execute a job synchronously on the calling thread.

        The *affinity* parameter is accepted but ignored — standalone mode
        has no thread scheduling.
        """
        return {
            "request_id": action_name,
            "affinity": affinity,
            "success": True,
            "output": payload,
            "error": None,
        }

    def submit_callable(
        self,
        request_id: str,
        task: Callable[[], Any],
        affinity: str = "any",
        timeout_ms: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Execute a callable synchronously."""
        with self._lock:
            try:
                output = task()
                return {
                    "request_id": request_id,
                    "affinity": affinity,
                    "success": True,
                    "output": output,
                    "error": None,
                }
            except Exception as exc:
                return {
                    "request_id": request_id,
                    "affinity": affinity,
                    "success": False,
                    "output": None,
                    "error": str(exc),
                }

    def dispatch_callable(self, func: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        """Run *func* through the core callable-dispatcher protocol.

        Core 0.17.x routes in-process skill scripts through
        ``BaseDccCallableDispatcher.dispatch_callable``.  Standalone Maya
        has no UI pump to marshal onto, but it still needs the same
        serialization guarantee as ``submit_callable`` because Maya's
        process-global API is not safe to enter concurrently from HTTP
        worker threads.
        """
        kwargs.pop("context", None)
        kwargs.pop("action_name", None)
        kwargs.pop("skill_name", None)
        kwargs.pop("execution", None)
        kwargs.pop("thread_affinity", None)
        kwargs.pop("affinity", None)
        kwargs.pop("timeout_hint_secs", None)
        kwargs.pop("timeout_ms", None)
        with self._lock:
            return func(*args, **kwargs)

    def submit_async_callable(
        self,
        request_id: str,
        task: Callable[[], Any],
        *,
        job_id: Optional[str] = None,
        progress_token: Optional[str] = None,
        on_complete: Optional[Callable[[Dict[str, Any]], None]] = None,
        affinity: str = "any",
        timeout_ms: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Execute a callable synchronously and invoke ``on_complete``.

        Standalone mode has no background queue, so this executes immediately
        on the calling thread and returns a completed envelope.  The
        ``on_complete`` callback, if provided, is called before returning.
        """
        result = self.submit_callable(request_id, task, affinity, timeout_ms)
        result["job_id"] = job_id
        result["status"] = "completed" if result.get("success") else "failed"
        if on_complete is not None:
            try:
                on_complete(result)
            except Exception as exc:  # pragma: no cover
                logger.warning(
                    "MayaStandaloneDispatcher.submit_async_callable on_complete raised: %s",
                    exc,
                )
        return result

    def supported(self) -> List[str]:
        """Return supported affinity values."""
        return ["any", "main"]

    def capabilities(self) -> Dict[str, bool]:
        """Return capability flags."""
        return {
            "supports_main_thread": True,
            "supports_named_threads": False,
            "supports_any_thread": True,
            "supports_time_slicing": False,
        }
