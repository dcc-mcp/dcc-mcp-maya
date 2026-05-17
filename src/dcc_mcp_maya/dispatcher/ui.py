"""Interactive Maya UI-thread dispatcher.

Hosts :class:`MayaUiDispatcher`, built on core :class:`~dcc_mcp_core.HostUiDispatcherBase`.
"""

from __future__ import annotations

import logging
from typing import Any, Callable, Tuple

from dcc_mcp_core import HostUiDispatcherBase

logger = logging.getLogger(__name__)


class MayaUiDispatcher(HostUiDispatcherBase):
    """Thread-affinity aware dispatcher for interactive Maya sessions.

    - ``"main"`` affinity jobs are queued and executed on Maya's UI thread
      via :class:`MayaUiPump` (or a one-shot ``executeDeferred`` fallback).
    - ``"any"`` affinity jobs run immediately on the calling thread.

    This class is **thread-safe**: ``submit()`` can be called from any thread.
    """

    def poke_host_pump(self) -> None:
        """Nudge Maya to drain the queue if no pump is installed."""
        try:
            import maya.utils  # noqa: PLC0415

            maya.utils.executeDeferred(self._deferred_drain)
        except ImportError:
            pass
        except Exception:
            pass

    def _deferred_drain(self) -> None:
        self.drain_queue(budget_ms=50)

    def drain_queue(self, budget_ms: float) -> Tuple[int, int]:
        executed, remaining = super().drain_queue(budget_ms)
        if executed > 0:
            logger.debug(
                "MayaUiPump: drained %d job(s), %d remaining",
                executed,
                remaining,
            )
        return executed, remaining

    def dispatch_callable(self, func: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        """Run *func* on Maya's UI thread (``BaseDccCallableDispatcher`` protocol)."""
        import uuid

        from dcc_mcp_core._server.inprocess_executor import timeout_hint_secs_to_ms

        context = kwargs.pop("context", None)
        timeout_hint_secs = kwargs.pop("timeout_hint_secs", None)
        if timeout_hint_secs is None and context is not None:
            timeout_hint_secs = getattr(context, "timeout_hint_secs", None)
        action_name = kwargs.pop("action_name", "")
        skill_name = kwargs.pop("skill_name", None)
        execution = kwargs.pop("execution", "sync")
        thread_affinity = kwargs.pop("thread_affinity", kwargs.pop("affinity", "main"))

        timeout_ms = timeout_hint_secs_to_ms(
            timeout_hint_secs,
            action_name=action_name,
            skill_name=skill_name,
            thread_affinity=thread_affinity,
            execution=execution,
        )

        request_id = f"dispatch_{uuid.uuid4().hex}"
        result = self.submit_callable(
            request_id=request_id,
            task=lambda: func(*args, **kwargs),
            affinity="main",
            timeout_ms=timeout_ms,
        )

        if not isinstance(result, dict):
            raise RuntimeError(f"dispatch_callable: unexpected result type {type(result)}")

        if not result.get("success", True):
            error_msg = result.get("error", "Unknown error")
            raise RuntimeError(f"dispatch_callable: {error_msg}")

        return result.get("output")
