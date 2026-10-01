"""Maya main-thread helpers shared by adapter teardown paths.

Why this module exists
======================

Maya's command engine is **not thread-safe**: ``maya.cmds`` calls issued from
a thread other than Maya's main thread are rejected (they raise, commonly
``TypeError``) or, worse, block inside Maya's native command engine.

Several adapter teardown paths need to remove ``scriptJob`` hooks (the idle
pump and the MCP resource scene-event hooks). ``MayaMcpServer.stop()`` was
calling those removals directly, so whenever ``stop()`` ran off the main
thread — which is exactly what the plug-in's *Restart MCP Server* menu does
via its ``dcc-mcp-restart`` daemon thread — every ``cmds.scriptJob(kill=...)``
failed. The failure was swallowed, but the owning object still reset its
bookkeeping, so the ids were lost and the live scriptJobs could never be
removed again. They stayed registered against a dispatcher that had already
been shut down.

:func:`run_on_main_thread` is the single choke point that keeps those calls
on Maya's main thread, and :func:`is_main_thread` lets callers decide
whether to do the work now or hand it to Maya's deferred queue.

See https://github.com/dcc-mcp/dcc-mcp-maya/issues/552
"""

from __future__ import annotations

import logging
import threading
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)

__all__ = ["is_main_thread", "run_on_main_thread"]


def is_main_thread() -> bool:
    """Return ``True`` when the caller is running on Maya's main thread.

    Uses :func:`threading.main_thread` so the answer is correct for the
    interpreter that Maya embeds, including ``mayapy`` and unit tests.
    """
    try:
        return threading.current_thread() is threading.main_thread()
    except Exception:  # noqa: BLE001 - never let the probe break teardown
        return True


def run_on_main_thread(fn: Callable[[], Any]) -> bool:
    """Run *fn* on Maya's main thread, deferring it when necessary.

    * On the main thread, *fn* runs immediately and ``True`` is returned.
    * Off the main thread, *fn* is handed to Maya's deferred queue via
      ``maya.utils.executeDeferred`` and ``False`` is returned. The call is
      fire-and-forget: the caller must **not** assume the work has happened
      when this returns, and must keep any state *fn* needs alive until it
      does run.

    Returns ``False`` when the work could not even be scheduled (no Maya);
    callers should then keep their state so a later retry can finish the job.

    Never raises — teardown paths must complete.
    """
    if is_main_thread():
        fn()
        return True

    deferred: Optional[Callable[..., Any]] = None
    try:
        import maya.utils  # noqa: PLC0415 - lazy: may be absent in tests

        deferred = maya.utils.executeDeferred
    except Exception as exc:  # noqa: BLE001
        logger.debug("main_thread: maya.utils unavailable (%s); cannot defer %r", exc, getattr(fn, "__name__", fn))
        return False

    try:
        deferred(fn)
        logger.debug(
            "main_thread: deferred %r to Maya's main thread (called from %s)",
            getattr(fn, "__name__", fn),
            threading.current_thread().name,
        )
        return True
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "main_thread: executeDeferred failed for %r: %s",
            getattr(fn, "__name__", fn),
            exc,
        )
        return False
