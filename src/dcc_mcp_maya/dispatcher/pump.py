"""Idle-event pump schedulers + dispatcher factory helpers.

Two pumps live here so they can share the ``budget_ms`` constants and
the same scriptJob hook idiom:

* :class:`MayaUiPump` drives :class:`MayaUiDispatcher` (Python-side).
* :class:`_CorePump` drives the Rust-backed
  :class:`PyPumpedDispatcher` from ``dcc-mcp-core``.

The :func:`create_dispatcher` / :func:`create_pumped_dispatcher` factory
helpers also live here because they return ``(dispatcher, pump)`` pairs
and need direct access to both pump constructors.

See: https://github.com/loonghao/dcc-mcp-maya/issues/85,
https://github.com/loonghao/dcc-mcp-maya/issues/128
"""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging
import time
from typing import Any, Dict, Optional, Tuple

# Import third-party modules
from dcc_mcp_core import PyPumpedDispatcher, PyStandaloneDispatcher  # noqa: F401

# Import local modules
from dcc_mcp_maya.dispatcher.standalone import MayaStandaloneDispatcher
from dcc_mcp_maya.dispatcher.ui import MayaUiDispatcher

logger = logging.getLogger(__name__)

# ── Constants ─────────────────────────────────────────────────────────────────

#: Default time budget (milliseconds) per idle-event pump cycle.
DEFAULT_BUDGET_MS = 8

#: Overrun threshold — any pump tick that spends more than ``budget_ms`` × this
#: multiplier counts as an ``overrun_cycles`` in :class:`MayaUiPump.stats`.
#: Matches the wording in issue #85: *"ticks that exceeded ``budget_ms * 2``"*.
OVERRUN_MULTIPLIER = 2.0


class MayaUiPump:
    """Cooperative time-slice scheduler driven by Maya's idle event.

    Registers a ``scriptJob(event=['idle', pump], protected=True)`` that
    fires each time Maya becomes idle.  The pump drains pending main-thread
    jobs from the attached :class:`MayaUiDispatcher` up to *budget_ms*
    milliseconds, then yields back to Maya so the viewport stays responsive.

    Parameters
    ----------
    dispatcher:
        The :class:`MayaUiDispatcher` whose main-thread queue to drain.
    budget_ms:
        Maximum milliseconds to spend draining per idle tick.  Lower
        values preserve more UI responsiveness; higher values improve
        throughput for long-running chains of small operations.
    """

    def __init__(
        self,
        dispatcher: MayaUiDispatcher,
        budget_ms: float = DEFAULT_BUDGET_MS,
    ) -> None:
        self._dispatcher = dispatcher
        self._budget_ms = budget_ms
        self._script_job_id: Optional[int] = None
        self._installed = False
        self._stats: Dict[str, float] = {
            "total_executed": 0,
            "total_cycles": 0,
            "total_elapsed_ms": 0.0,
            # Issue #85 §4 — ticks that exceeded ``budget_ms`` × OVERRUN_MULTIPLIER.
            # A non-zero value means ``MayaUiPump`` cannot chunk the work
            # further and the UI thread is being saturated by a single
            # non-cooperative ``cmds.*`` call. Skill authors should move
            # the offending logic behind :func:`check_maya_cancelled`
            # so it yields periodically.
            "overrun_cycles": 0,
            # Worst single-job wall-clock time observed across all cycles.
            # Feeds the ``dcc_maya_job_duration_seconds`` histogram (#87).
            "longest_job_ms": 0.0,
        }

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    @property
    def is_installed(self) -> bool:
        """``True`` if the idle scriptJob is currently active."""
        return self._installed

    @property
    def budget_ms(self) -> float:
        """Current time budget per idle-event cycle."""
        return self._budget_ms

    @budget_ms.setter
    def budget_ms(self, value: float) -> None:
        self._budget_ms = max(1.0, value)

    @property
    def stats(self) -> Dict[str, Any]:
        """Cumulative pump statistics."""
        return dict(self._stats)

    def install(self) -> bool:
        """Register the idle-event scriptJob with Maya.

        Returns ``True`` if installation succeeded or is already installed.
        """
        if self._installed:
            return True

        try:
            import maya.cmds as cmds  # noqa: PLC0415

            self._script_job_id = cmds.scriptJob(
                event=["idle", self._pump_tick],
                protected=True,
            )
            self._installed = True
            logger.info(
                "MayaUiPump installed (scriptJob=%d, budget=%.1f ms)",
                self._script_job_id,
                self._budget_ms,
            )
            return True
        except ImportError:
            logger.warning("MayaUiPump: maya.cmds not available — install skipped")
            return False
        except Exception as exc:
            logger.error("MayaUiPump: failed to install scriptJob: %s", exc)
            return False

    def uninstall(self) -> None:
        """Remove the idle-event scriptJob from Maya."""
        if not self._installed:
            return

        try:
            import maya.cmds as cmds  # noqa: PLC0415

            if self._script_job_id is not None:
                cmds.scriptJob(kill=self._script_job_id, force=True)
                logger.info("MayaUiPump uninstalled (scriptJob=%d)", self._script_job_id)
        except Exception as exc:
            logger.warning("MayaUiPump: error removing scriptJob: %s", exc)
        finally:
            self._script_job_id = None
            self._installed = False

    # ── Pump implementation ───────────────────────────────────────────────────

    def _pump_tick(self) -> None:
        """Idle-event callback: drain pending jobs within the budget.

        Important preemption caveat (issue #85 §4):
        ``drain_queue(budget_ms)`` only checks the deadline **between**
        jobs. When a skill script makes a single, non-cooperative
        ``cmds.*`` call that blocks the UI thread for seconds, this tick
        cannot preempt it — Maya itself has no tool to interrupt a
        running Python callable. The tick will be counted as an
        ``overrun_cycles`` so operators can tell the difference between
        "the pump is tuned too aggressively" and "a skill needs to be
        chunked behind :func:`check_maya_cancelled`".
        """
        start = time.monotonic()
        executed, remaining = self._dispatcher.drain_queue(self._budget_ms)

        elapsed_ms = (time.monotonic() - start) * 1000.0
        self._stats["total_executed"] += executed
        self._stats["total_cycles"] += 1
        self._stats["total_elapsed_ms"] += elapsed_ms

        # Overrun bookkeeping — see OVERRUN_MULTIPLIER.
        if elapsed_ms > self._budget_ms * OVERRUN_MULTIPLIER:
            self._stats["overrun_cycles"] += 1

        # ``longest_job_ms`` approximates the worst single-job duration.
        # ``drain_queue`` may execute multiple jobs per tick when each
        # finishes inside the budget; in that case the per-job worst is
        # bounded by ``elapsed_ms / max(executed, 1)``. When a single
        # job blows past the budget it dominates the tick, which is
        # exactly the case we want this metric to catch, so use the
        # larger of the two estimates.
        if executed > 0:
            avg_job_ms = elapsed_ms / executed
            worst_job_ms = elapsed_ms if executed == 1 else max(elapsed_ms, avg_job_ms)
            if worst_job_ms > self._stats["longest_job_ms"]:
                self._stats["longest_job_ms"] = worst_job_ms

        if remaining > 0:
            # Re-poke Maya so we get another idle event quickly
            try:
                import maya.cmds as cmds  # noqa: PLC0415

                cmds.refresh(force=True)
            except Exception:
                pass


# ── Factory helpers ───────────────────────────────────────────────────────────


def create_dispatcher(
    budget_ms: float = DEFAULT_BUDGET_MS,
) -> Tuple[Any, Optional[MayaUiPump]]:
    """Create the appropriate dispatcher for the current Maya environment.

    Returns a ``(dispatcher, pump)`` pair where *dispatcher* is a
    :class:`MayaUiDispatcher` (interactive) or
    :class:`MayaStandaloneDispatcher` (batch / ``mayapy``), and *pump* is a
    :class:`MayaUiPump` or ``None`` respectively.

    The returned :class:`MayaUiDispatcher` supports ``submit_callable`` for
    routing arbitrary Python callables to Maya's UI thread — required by the
    in-process skill executor.  Use :func:`create_pumped_dispatcher` when
    you want the Rust-backed :class:`PyPumpedDispatcher` (string-payload
    dispatch only) instead.

    Returns
    -------
    tuple[MayaUiDispatcher | MayaStandaloneDispatcher, MayaUiPump | None]
        A ``(dispatcher, pump)`` pair.  The pump is ``None`` in standalone mode.
    """
    try:
        import maya.cmds as cmds  # noqa: PLC0415

        is_batch = cmds.about(batch=True)
    except ImportError:
        is_batch = True

    if is_batch:
        return MayaStandaloneDispatcher(), None

    dispatcher = MayaUiDispatcher()
    pump = MayaUiPump(dispatcher, budget_ms=budget_ms)
    return dispatcher, pump


def create_pumped_dispatcher(
    budget_ms: float = DEFAULT_BUDGET_MS,
) -> Tuple[Any, Optional["_CorePump"]]:
    """Create a Rust-backed :class:`PyPumpedDispatcher` for the current Maya environment.

    This is an alternative to :func:`create_dispatcher` that returns the
    core's ``PyPumpedDispatcher`` instead of :class:`MayaUiDispatcher`.
    Use it when you need IPC-style string-payload dispatch routed through
    the Rust main-thread pump.

    .. note::
        ``PyPumpedDispatcher`` only supports ``submit(action_name, payload,
        affinity)`` where *payload* is a string.  It cannot dispatch arbitrary
        Python callables.  For in-process skill execution, the
        :class:`MayaUiDispatcher` returned by :func:`create_dispatcher` must
        be used.

    Returns
    -------
    tuple[PyPumpedDispatcher | MayaStandaloneDispatcher, _CorePump | None]
        A ``(dispatcher, pump)`` pair.  Returns
        ``(MayaStandaloneDispatcher(), None)`` when not inside an interactive
        Maya session or when ``PyPumpedDispatcher`` is not available.
    """
    try:
        import maya.cmds as cmds  # noqa: PLC0415

        is_batch = cmds.about(batch=True)
    except ImportError:
        is_batch = True

    if is_batch:
        return MayaStandaloneDispatcher(), None

    core_dispatcher = PyPumpedDispatcher(budget_ms=int(budget_ms))
    pump = _CorePump(core_dispatcher, budget_ms=budget_ms)
    return core_dispatcher, pump


class _CorePump:
    """Idle-event pump adapter for :class:`PyPumpedDispatcher`.

    Wraps :class:`PyPumpedDispatcher` in the same scriptJob-based idle hook
    that :class:`MayaUiPump` uses for :class:`MayaUiDispatcher`, so callers
    can treat both pump types identically (``install()`` / ``uninstall()``).

    Parameters
    ----------
    dispatcher:
        A :class:`PyPumpedDispatcher` instance whose :meth:`pump` method
        should be called on each idle tick.
    budget_ms:
        Maximum milliseconds for each pump call.  Passed to
        :meth:`PyPumpedDispatcher.pump_with_budget`.
    """

    def __init__(self, dispatcher: Any, budget_ms: float = DEFAULT_BUDGET_MS) -> None:
        self._dispatcher = dispatcher
        self._budget_ms = budget_ms
        self._script_job_id: Optional[int] = None
        self._installed = False

    @property
    def is_installed(self) -> bool:
        """``True`` if the idle scriptJob is currently active."""
        return self._installed

    def install(self) -> bool:
        """Register the idle-event scriptJob with Maya."""
        if self._installed:
            return True
        try:
            import maya.cmds as cmds  # noqa: PLC0415

            self._script_job_id = cmds.scriptJob(
                event=["idle", self._pump_tick],
                protected=True,
            )
            self._installed = True
            logger.info(
                "_CorePump installed (scriptJob=%d, budget=%.1f ms)",
                self._script_job_id,
                self._budget_ms,
            )
            return True
        except ImportError:
            logger.warning("_CorePump: maya.cmds not available — install skipped")
            return False
        except Exception as exc:
            logger.error("_CorePump: failed to install scriptJob: %s", exc)
            return False

    def uninstall(self) -> None:
        """Remove the idle-event scriptJob from Maya."""
        if not self._installed:
            return
        try:
            import maya.cmds as cmds  # noqa: PLC0415

            if self._script_job_id is not None:
                cmds.scriptJob(kill=self._script_job_id, force=True)
                logger.info("_CorePump uninstalled (scriptJob=%d)", self._script_job_id)
        except Exception as exc:
            logger.warning("_CorePump: error removing scriptJob: %s", exc)
        finally:
            self._script_job_id = None
            self._installed = False

    def _pump_tick(self) -> None:
        """Idle-event callback — drain pending Rust-side main-thread jobs."""
        try:
            stats = self._dispatcher.pump_with_budget(int(self._budget_ms))
            remaining = stats.get("remaining", 0) if isinstance(stats, dict) else 0
            if remaining > 0:
                try:
                    import maya.cmds as cmds  # noqa: PLC0415

                    cmds.refresh(force=True)
                except Exception:
                    pass
        except Exception as exc:
            logger.debug("_CorePump._pump_tick error: %s", exc)
