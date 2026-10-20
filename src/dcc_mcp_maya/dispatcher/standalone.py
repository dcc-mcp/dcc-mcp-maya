"""Cooperative main-thread dispatch for mayapy / batch Maya."""

from __future__ import annotations

import threading
from typing import Any, Callable, Dict, Optional, Tuple

from dcc_mcp_maya.dispatcher.ui import MayaUiDispatcher


class MayaStandaloneDispatcher(MayaUiDispatcher):
    """Queue scene calls for the thread that initialized Maya.

    There is no idle event loop in mayapy. The application's main loop must
    call ``drain_queue(budget_ms)`` while serving requests; waiting on an Event
    alone cannot service Maya calls. Pure ``affinity="any"`` work stays inline.
    Core owns the queue, HTTP attachment, cancellation, timeouts and shutdown.
    """

    def poke_host_pump(self) -> None:
        # Batch Maya has no executeDeferred event loop; the caller pumps.
        pass

    def submit_callable(
        self,
        request_id: str,
        task: Callable[[], Any],
        affinity: str = "main",
        timeout_ms: Optional[int] = None,
    ) -> Dict[str, Any]:
        if affinity == "main" and threading.current_thread() is threading.main_thread():
            result = super().submit_callable(request_id, task, "any", timeout_ms)
            result["affinity"] = "main"
            return result
        return super().submit_callable(request_id, task, affinity, timeout_ms)

    def drain_queue(self, budget_ms: float = 8) -> Tuple[int, int]:
        if threading.current_thread() is not threading.main_thread():
            raise RuntimeError("Maya standalone must be pumped on the main thread")
        return super().drain_queue(budget_ms)
