"""Runtime readiness wiring for :class:`MayaMcpServer` (issue #184).

Maya's embedded MCP HTTP server publishes itself to the ``FileRegistry``
long before Maya's main thread has finished booting.  During that window
``list_dcc_instances`` reports ``status: "available"``, any
``tools/call`` with ``affinity: main`` is accepted and then **blocks**
until Maya's main thread pumps, and the gateway's first auto-aggregation
probe fails with *"not a DCC MCP HTTP endpoint"* because the fresh HTTP
listener has not answered its first request yet.

Core 0.14.28 first exposed the three-state probe in Rust and its Python
binding (``dcc_mcp_core.ReadinessProbe`` + ``McpHttpServer.set_readiness_probe``);
``pyproject.toml`` now pins the floor at 0.17.31, the Python 3.7-capable
core release.  This module owns the **Maya-specific** half of the contract:

* flip ``dispatcher = true`` the moment the in-process executor is wired;
* schedule a cheap no-op job on the UI dispatcher and flip ``dcc = true``
  from its completion callback — guaranteeing that ``dcc`` is only green
  once Maya's main thread has actually pumped one job;
* expose an env knob (:data:`ENV_READINESS_TIMEOUT_SECS`) so orchestrators
  can bound how long a cold Maya may stall before they consider
  ``/v1/readyz`` permanently red.

SOLID notes
-----------
* **Single Responsibility** — this module *only* wires Maya lifecycle
  events onto a :class:`dcc_mcp_core.ReadinessProbe`; it owns neither the
  probe's state (Rust does) nor the dispatcher (:class:`MayaMcpServer`
  does).
* **Open/Closed** — the dispatcher-probe strategy is injectable
  (:attr:`ReadinessBinder.probe_scheduler`), so tests can verify the
  flip without running a live Maya event loop.
"""

from __future__ import annotations

import logging
import os
from typing import Any, Callable, Optional

from dcc_mcp_core import ReadinessProbe

logger = logging.getLogger(__name__)

#: Environment variable that bounds how long orchestrators are willing
#: to wait for a cold Maya before readiness is considered red.  Parsed
#: as a positive integer number of seconds.  Unset → no Maya-side
#: timeout; the gateway / orchestrator decides.
ENV_READINESS_TIMEOUT_SECS = "DCC_MCP_MAYA_READINESS_TIMEOUT_SECS"

#: Request ID used for the no-op probe job scheduled on the UI
#: dispatcher.  Kept stable so operators grepping the Maya log can
#: correlate the "readiness flip" line with the exact job.
READINESS_PROBE_REQUEST_ID = "dcc_mcp_maya__readiness__dcc_ready_probe"


# ---------------------------------------------------------------------------
# Env-var resolution
# ---------------------------------------------------------------------------


def resolve_readiness_timeout_secs(
    readiness_timeout_secs: Optional[int] = None,
) -> Optional[int]:
    """Resolve :data:`ENV_READINESS_TIMEOUT_SECS` into a positive integer.

    Priority: explicit argument > env var > ``None``.  ``None`` means
    "no Maya-side timeout — let the orchestrator decide".  Invalid
    values (non-integer, ``<= 0``) collapse to ``None`` and log a
    warning so a typo never kills startup.
    """
    if readiness_timeout_secs is not None:
        try:
            val = int(readiness_timeout_secs)
        except (TypeError, ValueError):
            return None
        return val if val > 0 else None

    raw = os.environ.get(ENV_READINESS_TIMEOUT_SECS)
    if raw is None:
        return None
    raw = raw.strip()
    if not raw:
        return None
    try:
        val = int(raw)
    except ValueError:
        logger.warning(
            "Ignoring invalid %s=%r (expected positive integer seconds)",
            ENV_READINESS_TIMEOUT_SECS,
            raw,
        )
        return None
    if val <= 0:
        logger.warning(
            "Ignoring non-positive %s=%r (expected positive integer seconds)",
            ENV_READINESS_TIMEOUT_SECS,
            raw,
        )
        return None
    return val


# ---------------------------------------------------------------------------
# Dispatcher probe helpers
# ---------------------------------------------------------------------------


ProbeScheduler = Callable[[Any, Callable[[], None]], bool]
"""Dispatcher-agnostic scheduler: ``(dispatcher, on_done) -> scheduled?``.

Returns ``True`` when ``on_done`` is guaranteed to eventually be called
(synchronously on standalone dispatchers; after the next pump cycle on
UI dispatchers).
"""


def _default_probe_scheduler(dispatcher: Any, on_done: Callable[[], None]) -> bool:
    """Schedule a dcc-ready probe on *dispatcher*.

    Two dispatcher shapes are in play at runtime:

    * **Full callable protocol** (:class:`MayaUiDispatcher` /
      :class:`MayaStandaloneDispatcher`): implements
      :meth:`submit_async_callable` with an ``on_complete`` callback.
      Submit a no-op job at ``affinity="main"`` and flip ``dcc`` from
      the callback — guaranteeing the bit only flips after Maya's
      main thread has actually pumped one job.
    * **Post/tick protocol** (core's ``BlockingDispatcher`` /
      ``QueueDispatcher`` attached via the plugin bootstrap): no
      ``submit_async_callable`` hook and no per-job callback API, so
      we trust the dispatcher to pump correctly and flip ``dcc``
      immediately.  The alternative — leaving ``dcc`` red forever —
      would make ``/v1/readyz`` return 503 for every real-world
      plugin-driven server.
    """
    submit_async = getattr(dispatcher, "submit_async_callable", None)
    if submit_async is None:
        # Post/tick-style dispatcher — flip optimistically.
        on_done()
        return True

    def _on_complete(_result: Any) -> None:  # noqa: ARG001 — signature contract
        on_done()

    submit_async(
        request_id=READINESS_PROBE_REQUEST_ID,
        task=lambda: None,
        affinity="main",
        timeout_ms=5_000,
        on_complete=_on_complete,
    )
    return True


# ---------------------------------------------------------------------------
# Maya-side binder — wraps a core ReadinessProbe with lifecycle hooks
# ---------------------------------------------------------------------------


class ReadinessBinder:
    """Drive a :class:`dcc_mcp_core.ReadinessProbe` across a Maya lifecycle.

    Usage (called once from ``MayaMcpServer.__init__``)::

        binder = ReadinessBinder()
        binder.bind(server)
        # ``binder.report()`` lands green synchronously when no host
        # dispatcher is attached (inline executor path); otherwise it
        # transitions to all-green after the first main-thread pump.

    Calling :meth:`bind` twice on the same server is a no-op.  The core
    :class:`ReadinessProbe` is published to the inner Rust
    ``McpHttpServer`` via ``set_readiness_probe`` so that
    ``/v1/readyz`` serves honest values.

    Parameters
    ----------
    timeout_secs:
        Advisory Maya-side timeout (seconds) for how long a cold Maya
        can stall before callers should consider ``dcc`` permanently
        red.  Consumed by orchestration layers; this class does *not*
        auto-fail the probe when the timeout elapses — a hung Maya is
        better reported as "still booting" than as a synthetic error.
    probe_scheduler:
        Strategy for scheduling the dcc-ready probe on the attached
        dispatcher.  Override in tests to avoid depending on a real
        :class:`MayaUiDispatcher` pump.
    """

    def __init__(
        self,
        *,
        timeout_secs: Optional[int] = None,
        probe_scheduler: Optional[ProbeScheduler] = None,
    ) -> None:
        self.timeout_secs: Optional[int] = resolve_readiness_timeout_secs(
            timeout_secs,
        )
        self.probe: ReadinessProbe = ReadinessProbe()
        self.probe_scheduler: ProbeScheduler = probe_scheduler or _default_probe_scheduler
        # Populated by :meth:`bind` so tests can assert what we wired.
        self.bound_server: Any = None
        self.bound_dispatcher: Any = None
        self.dcc_scheduled: bool = False
        self.published_to_server: bool = False

    # ── Public API ──────────────────────────────────────────────────────

    def report(self) -> dict:
        """Return the current three-state readiness snapshot as a dict.

        Delegates to :meth:`dcc_mcp_core.ReadinessProbe.report`.  Keys:
        ``process`` / ``dispatcher`` / ``dcc``.
        """
        return self.probe.report()

    def is_ready(self) -> bool:
        """Return ``True`` when all three bits are green."""
        return self.probe.is_ready()

    def bind(self, server: Any) -> bool:
        """Wire the probe into *server*.

        Steps:

        1. Publish :attr:`probe` to the inner Rust ``McpHttpServer`` via
           :meth:`McpHttpServer.set_readiness_probe`.  This is what
           causes ``/v1/readyz`` to serve honest values.
        2. Flip ``dispatcher = true`` unconditionally — by the time
           :meth:`bind` is called, :meth:`MayaMcpServer.__init__` has
           already registered ``HostExecutionBridge``, so the Rust
           handler routing is live.
        3. If no host dispatcher is attached
           (``server._maya_dispatcher is None``), the inline executor
           runs jobs on the HTTP worker thread — there is **no** Maya
           main thread to wait on — so flip ``dcc = true`` immediately.
        4. Otherwise, schedule a no-op probe on the host dispatcher so
           the first main-thread pump flips ``dcc = true``.  On
           :class:`MayaStandaloneDispatcher` that callback fires
           synchronously; on a live Maya UI dispatcher it fires on the
           first idle tick once the scene is up.

        Returns
        -------
        bool
            ``True`` when binding left the probe fully ready or
            successfully scheduled the final dcc flip.
        """
        if self.bound_server is server:
            return self.dcc_scheduled
        self.bound_server = server

        # Step 1 — publish to the inner Rust server.
        server._server.set_readiness_probe(self.probe)
        self.published_to_server = True

        # Step 2 — dispatcher bit: the executor is always wired by the
        # time we arrive here, so handler routing is live regardless of
        # whether a Maya UI dispatcher is present.
        self.mark_dispatcher_ready()

        # Step 3 / 4 — dcc bit.
        dispatcher = server._maya_dispatcher
        if dispatcher is None:
            # Inline execution bridge path:
            # every ``tools/call`` runs on the HTTP worker thread — there
            # is no separate Maya main thread to wait on, so the "dcc"
            # bit is meaningful only as "handler routing is live", which
            # is already true.  Collapse to green.
            self.bound_dispatcher = None
            self.mark_dcc_ready()
            self.dcc_scheduled = True
            return True

        self.bound_dispatcher = dispatcher
        self.dcc_scheduled = bool(self.probe_scheduler(dispatcher, self.mark_dcc_ready))
        return self.dcc_scheduled

    def mark_dispatcher_ready(self, value: bool = True) -> None:
        """Flip the ``dispatcher`` bit.  Idempotent."""
        self.probe.set_dispatcher_ready(value)
        if value:
            logger.debug("readiness: dispatcher=true")

    def mark_dcc_ready(self, value: bool = True) -> None:
        """Flip the ``dcc`` bit.  Typically called from the probe callback."""
        self.probe.set_dcc_ready(value)
        if value:
            logger.info("[maya] readiness: dcc-ready — main thread is pumping")


# ---------------------------------------------------------------------------
# Module-level convenience
# ---------------------------------------------------------------------------


def install_readiness(
    server: Any,
    *,
    timeout_secs: Optional[int] = None,
    probe_scheduler: Optional[ProbeScheduler] = None,
) -> ReadinessBinder:
    """One-shot helper used by :class:`MayaMcpServer.__init__`."""
    binder = ReadinessBinder(
        timeout_secs=timeout_secs,
        probe_scheduler=probe_scheduler,
    )
    binder.bind(server)
    return binder
