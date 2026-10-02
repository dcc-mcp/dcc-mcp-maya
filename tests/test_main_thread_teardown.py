"""Regression tests for issue #552 — Maya freezes on MCP server stop/restart.

``MayaMcpServer.stop()`` removes ``scriptJob`` hooks (the idle pump and the
MCP resource scene-event hooks).  ``maya.cmds`` is **not** thread-safe, and
the plug-in's *Restart MCP Server* runs ``stop_server()`` on the
``dcc-mcp-restart`` daemon thread, so every ``cmds.scriptJob(kill=...)`` was
rejected by Maya (``TypeError``) and swallowed.  Because the owning objects
still reset their bookkeeping, the ids were lost and the live scriptJobs
could never be removed again.

These tests pin the contract: off the main thread the teardown is deferred to
Maya's main thread and the ids are retained until the removal actually
happens.

Three guarantees are covered:

1. Deferral + retention (issue #552, the original fix).
2. **Partial** teardown: when only *some* ``scriptJob(kill=...)`` calls fail,
   the ids that were actually killed are dropped and only the survivors are
   retained (PR #555 P2 follow-up).
3. Restart ordering: a queued teardown from the *old* pump/binder never kills
   the *replacement* pump/binder's job, even though Maya 2022 drains
   ``executeDeferred`` LIFO (PR #555 P3 follow-up).

.. note::
   Maya 2022's ``executeDeferred`` is LIFO, not FIFO.  A test that assumes
   FIFO passes on a fake queue but hides the real interleaving.
"""

from __future__ import annotations

import sys
import threading
import types

import pytest

from dcc_mcp_maya import _main_thread as main_thread_mod
from dcc_mcp_maya import _resources as resources_mod
from dcc_mcp_maya.dispatcher import pump as pump_mod


class FakeCmds:
    """Stand-in for ``maya.cmds`` that records ``scriptJob`` calls.

    Two independent refusal switches, so tests can express both failure
    shapes:

    * ``refuse_kill = True`` — every kill fails (all-or-nothing);
    * ``refuse_kill_ids = {155}`` — only those ids fail (partial failure,
      the shape that actually happens in production).
    """

    def __init__(self) -> None:
        self.calls: list = []
        self.refuse_kill = False
        self.refuse_kill_ids: set = set()
        self.kill_raises: type = TypeError

    def scriptJob(self, *args, **kwargs):
        self.calls.append((args, kwargs))
        if "kill" in kwargs:
            if self.refuse_kill or kwargs["kill"] in self.refuse_kill_ids:
                raise self.kill_raises("Invalid argument for flag 'kill'. Expected int, got NoneType")
            return None
        return 100 + len(self.calls)

    @property
    def killed_ids(self) -> list:
        """scriptJob ids passed to ``kill=``, in call order."""
        return [kwargs["kill"] for _, kwargs in self.calls if "kill" in kwargs]


class FakeMayaUtils:
    """Stand-in for ``maya.utils`` capturing deferred callbacks.

    Maya 2022's ``executeDeferred`` is **LIFO** — queueing A, B, C runs them
    as C, B, A (measured on Maya 2022 / Python 3.7.7).  :meth:`drain`
    reproduces that order by default so ordering assertions match the real
    host; pass ``fifo=True`` to model a FIFO host instead.
    """

    def __init__(self, fifo: bool = False) -> None:
        self.deferred: list = []
        self.fifo = fifo

    def executeDeferred(self, fn, *args, **kwargs):
        self.deferred.append(fn)

    def drain(self) -> None:
        """Run every queued callback the way Maya's main thread would.

        Drains in batches until the queue is empty, so a callback that
        enqueues more work is picked up too.
        """
        while self.deferred:
            fn = self.deferred.pop(0) if self.fifo else self.deferred.pop()
            fn()


@pytest.fixture
def fake_maya(monkeypatch, request):
    """Install fake ``maya``, ``maya.cmds`` and ``maya.utils`` modules.

    Indirectly parametrisable with a bool to flip the deferred-queue drain
    order (``False``/default = Maya 2022 LIFO, ``True`` = FIFO).
    """
    fifo = bool(getattr(request, "param", False))
    cmds = FakeCmds()
    utils = FakeMayaUtils(fifo=fifo)

    maya = types.ModuleType("maya")
    maya_cmds = types.ModuleType("maya.cmds")
    maya_utils = types.ModuleType("maya.utils")

    for name, value in vars(FakeCmds).items():
        if not name.startswith("__") and callable(value):
            setattr(maya_cmds, name, getattr(cmds, name))
    maya_utils.executeDeferred = utils.executeDeferred
    maya.cmds = maya_cmds
    maya.utils = maya_utils

    monkeypatch.setitem(sys.modules, "maya", maya)
    monkeypatch.setitem(sys.modules, "maya.cmds", maya_cmds)
    monkeypatch.setitem(sys.modules, "maya.utils", maya_utils)
    return cmds, utils


def _run_in_worker(fn):
    """Run *fn* on a worker thread, returning ``(exception, )``."""
    box: dict = {}

    def _target():
        try:
            fn()
        except BaseException as exc:  # noqa: BLE001
            box["exc"] = exc

    thread = threading.Thread(target=_target, name="dcc-mcp-restart", daemon=True)
    thread.start()
    thread.join(timeout=10.0)
    assert not thread.is_alive(), "worker thread hung"
    return box.get("exc")


def _make_pump():
    pump = pump_mod.MayaUiPump.__new__(pump_mod.MayaUiPump)
    pump._dispatcher = None
    pump._budget_ms = 8.0
    pump._script_job_id = 153
    pump._installed = True
    pump._stats = {}
    return pump


# ── MayaUiPump ──────────────────────────────────────────────────────────────


def test_pump_uninstall_off_main_thread_never_touches_cmds(fake_maya):
    """maya.cmds must not be called from a worker thread (issue #552)."""
    cmds, utils = fake_maya
    pump = _make_pump()

    exc = _run_in_worker(pump.uninstall)

    assert exc is None
    assert cmds.calls == [], "cmds.scriptJob must not run off the main thread"
    assert utils.deferred, "teardown must be handed to Maya's main thread"
    # The id is retained so the deferred removal can still find the job.
    assert pump._script_job_id == 153
    assert pump._installed is True


def test_pump_deferred_uninstall_kills_script_job_on_main_thread(fake_maya):
    """Once on the main thread the scriptJob is killed and state cleared."""
    cmds, utils = fake_maya
    pump = _make_pump()

    _run_in_worker(pump.uninstall)
    for fn in utils.deferred:
        fn()

    assert ("kill", 153) in [(k.get("kill"), v) for (_, k), v in zip(cmds.calls, [None] * len(cmds.calls))] or any(
        kwargs.get("kill") == 153 for _, kwargs in cmds.calls
    )
    assert pump._script_job_id is None
    assert pump._installed is False


def test_pump_uninstall_keeps_id_when_kill_fails(fake_maya, monkeypatch):
    """A failed kill must not discard the id — otherwise the job leaks."""
    cmds, _utils = fake_maya
    cmds.refuse_kill = True
    pump = _make_pump()

    # Called on the main thread so no deferral happens.
    pump.uninstall()

    assert any(kwargs.get("kill") == 153 for _, kwargs in cmds.calls)
    assert pump._script_job_id == 153, "id must survive a failed kill so a retry can clean up"
    assert pump._installed is True


# ── MayaResourceBinder ──────────────────────────────────────────────────────


def _make_binder():
    binder = resources_mod.MayaResourceBinder.__new__(resources_mod.MayaResourceBinder)
    binder._lock = threading.Lock()
    binder._pending_publish = False
    binder._publish_timer = None
    binder._unbound = False
    binder.scene_event_ids = [154, 155, 156]
    return binder


def test_resource_unbind_off_main_thread_defers_and_retains_ids(fake_maya, monkeypatch):
    """Scene-event scriptJobs must be removed on Maya's main thread."""
    cmds, utils = fake_maya
    removed: list = []
    monkeypatch.setattr(resources_mod, "_default_event_remover", lambda ids: removed.append(list(ids)))

    binder = _make_binder()
    exc = _run_in_worker(binder.unbind)

    assert exc is None
    assert removed == [], "scriptJobs must not be killed off the main thread"
    assert binder.scene_event_ids == [154, 155, 156], "ids must be retained for the deferred removal"
    assert utils.deferred, "removal must be scheduled on Maya's main thread"


def test_resource_deferred_unbind_removes_ids_on_main_thread(fake_maya, monkeypatch):
    """The deferred retry must actually run (not short-circuit on _unbound)."""
    cmds, utils = fake_maya
    removed: list = []
    monkeypatch.setattr(resources_mod, "_default_event_remover", lambda ids: removed.append(list(ids)))

    binder = _make_binder()
    _run_in_worker(binder.unbind)
    assert binder._unbound is True, "unbind() marks the binder unbound immediately"

    for fn in utils.deferred:
        fn()

    assert removed == [[154, 155, 156]]
    assert binder.scene_event_ids == []


def test_resource_unbind_on_main_thread_is_synchronous(fake_maya, monkeypatch):
    """On the main thread nothing changes: removal still happens inline."""
    cmds, utils = fake_maya
    removed: list = []
    monkeypatch.setattr(resources_mod, "_default_event_remover", lambda ids: removed.append(list(ids)))

    binder = _make_binder()
    binder.unbind()

    assert removed == [[154, 155, 156]]
    assert binder.scene_event_ids == []
    assert utils.deferred == [], "no deferral needed on the main thread"


# ────────────────────────────────────────────────────────────────────────────
# PR #555 P2 follow-up — partial teardown must not forget the survivors
# ────────────────────────────────────────────────────────────────────────────


def test_default_event_remover_returns_empty_list_when_every_kill_succeeds(fake_maya):
    """A clean teardown reports nothing left behind."""
    cmds, _utils = fake_maya

    failed = resources_mod._default_event_remover([154, 155])

    assert failed == []
    assert cmds.killed_ids == [154, 155]


def test_default_event_remover_reports_only_the_ids_it_could_not_kill(fake_maya):
    """One refusing id must not mask the ids that were killed successfully."""
    cmds, _utils = fake_maya
    cmds.refuse_kill_ids = {155}

    failed = resources_mod._default_event_remover([154, 155, 156])

    assert failed == [155]
    assert cmds.killed_ids == [154, 155, 156], "every id must still be attempted"


def test_resource_unbind_keeps_all_ids_when_every_kill_fails(fake_maya):
    """All-fail path: dropping any id here is the leak issue #552 is about."""
    cmds, _utils = fake_maya
    cmds.refuse_kill = True

    binder = _make_binder()
    binder.unbind()

    assert cmds.killed_ids == [154, 155, 156]
    assert binder.scene_event_ids == [154, 155, 156], "no id may be forgotten when nothing was killed"


def test_resource_unbind_keeps_only_the_failed_id_when_kill_partially_fails(fake_maya):
    """Mixed path: killed ids are dropped, the survivor is retained.

    This is the production shape (a handful of events, one refuses) and the
    half an all-or-nothing fake cannot see: it pins that the *successful*
    kills are also forgotten, not just the failed one kept.
    """
    cmds, _utils = fake_maya
    cmds.refuse_kill_ids = {155}

    binder = _make_binder()
    binder.unbind()

    assert cmds.killed_ids == [154, 155, 156]
    assert binder.scene_event_ids == [155]


def test_resource_retry_after_partial_failure_can_still_clear_the_survivor(fake_maya):
    """A later retry finds the retained id — retention is not a dead end.

    ``unbind()`` flags the binder unbound immediately, so the retry goes
    through :meth:`_remove_scene_events` (the same entry point the deferred
    hop uses); the ``_unbound`` guard must not block it.
    """
    cmds, _utils = fake_maya
    cmds.refuse_kill_ids = {155}

    binder = _make_binder()
    binder.unbind()
    assert binder.scene_event_ids == [155]

    cmds.refuse_kill_ids = set()
    binder._remove_scene_events()

    assert cmds.killed_ids == [154, 155, 156, 155]
    assert binder.scene_event_ids == []


def test_resource_unbind_keeps_ids_when_the_remover_itself_raises(fake_maya, monkeypatch):
    """A remover that blows up entirely must not be read as a clean teardown."""

    def _boom(ids):
        raise RuntimeError("maya is shutting down")

    monkeypatch.setattr(resources_mod, "_default_event_remover", _boom)

    binder = _make_binder()
    binder.unbind()

    assert binder.scene_event_ids == [154, 155, 156]


# ────────────────────────────────────────────────────────────────────────────
# PR #555 P3.1 follow-up — the Rust-backed _CorePump shares the contract
# ────────────────────────────────────────────────────────────────────────────


def _make_core_pump():
    pump = pump_mod._CorePump.__new__(pump_mod._CorePump)
    pump._dispatcher = None
    pump._budget_ms = 8.0
    pump._script_job_id = 157
    pump._installed = True
    return pump


def test_core_pump_uninstall_off_main_thread_defers_and_retains_id(fake_maya):
    """``create_pumped_dispatcher``'s pump must honour issue #552 too."""
    cmds, utils = fake_maya
    pump = _make_core_pump()

    exc = _run_in_worker(pump.uninstall)

    assert exc is None
    assert cmds.calls == [], "cmds.scriptJob must not run off the main thread"
    assert utils.deferred, "teardown must be handed to Maya's main thread"
    assert pump._script_job_id == 157
    assert pump.is_installed is True


def test_core_pump_deferred_uninstall_kills_script_job_on_main_thread(fake_maya):
    """The queued teardown still runs — the guard is not a short-circuit."""
    cmds, utils = fake_maya
    pump = _make_core_pump()

    _run_in_worker(pump.uninstall)
    utils.drain()

    assert cmds.killed_ids == [157]
    assert pump._script_job_id is None
    assert pump.is_installed is False


def test_core_pump_uninstall_keeps_id_when_kill_fails(fake_maya):
    """Same retention contract as :class:`MayaUiPump`."""
    cmds, _utils = fake_maya
    cmds.refuse_kill = True
    pump = _make_core_pump()

    pump.uninstall()

    assert cmds.killed_ids == [157]
    assert pump._script_job_id == 157, "id must survive a failed kill so a retry can clean up"
    assert pump.is_installed is True


# ────────────────────────────────────────────────────────────────────────────
# PR #555 P3.2 follow-up — restart ordering (Maya 2022 drains LIFO)
# ────────────────────────────────────────────────────────────────────────────


def test_fake_deferred_queue_drains_lifo_like_maya_2022(fake_maya):
    """Pin the fake's drain order to the measured Maya 2022 behaviour.

    ``executeDeferred`` is LIFO on Maya 2022 (queue A, B, C -> runs C, B, A).
    A fake that drained FIFO would make every ordering assertion below
    silently meaningless, so the assumption is guarded here.
    """
    _cmds, utils = fake_maya
    seen: list = []

    utils.executeDeferred(lambda: seen.append("first"))
    utils.executeDeferred(lambda: seen.append("second"))
    utils.drain()

    assert seen == ["second", "first"]


@pytest.mark.parametrize("fake_maya", [False, True], indirect=True)
def test_restart_old_pump_teardown_never_kills_the_replacement_job(fake_maya):
    """Restart safety: the queued old teardown only knows its own id.

    *Restart MCP Server* runs ``stop()`` on a daemon thread, so the old
    pump's ``scriptJob(kill=...)`` is queued via ``executeDeferred`` and the
    replacement pump is installed afterwards.  Maya 2022 drains that queue
    LIFO, i.e. the pending old teardown runs *after* the restart — the worst
    interleaving.  It stays safe only because the queued callback is a bound
    method of the **old** pump and carries nothing but that pump's id.

    Run under both drain orders: the guarantee must not depend on it.
    """
    cmds, utils = fake_maya

    old = _make_pump()  # installed with scriptJob 153
    assert _run_in_worker(old.uninstall) is None
    assert utils.deferred, "the old teardown must be queued, not run inline"

    new = _make_pump()
    new._script_job_id = 200

    utils.drain()

    assert cmds.killed_ids == [153], "only the old pump's job may be killed"
    assert old._script_job_id is None
    assert old.is_installed is False
    assert new._script_job_id == 200, "the replacement pump's job must survive the restart"
    assert new.is_installed is True


@pytest.mark.parametrize("fake_maya", [False, True], indirect=True)
def test_restart_old_binder_teardown_never_kills_the_replacement_ids(fake_maya):
    """Binder-side mirror of the restart ordering guarantee.

    The queued callback is ``old_binder._remove_scene_events``; it must
    operate on the old binder's ids only and leave the replacement binder's
    freshly installed events alive.
    """
    cmds, utils = fake_maya

    old = _make_binder()  # ids [154, 155, 156]
    assert _run_in_worker(old.unbind) is None
    assert utils.deferred, "the old teardown must be queued, not run inline"

    new = _make_binder()
    new.scene_event_ids = [170, 171]

    utils.drain()

    assert cmds.killed_ids == [154, 155, 156], "only the old binder's events may be killed"
    assert old.scene_event_ids == []
    assert new.scene_event_ids == [170, 171], "the replacement binder's events must survive the restart"


# ── _main_thread helper ─────────────────────────────────────────────────────


def test_run_on_main_thread_executes_inline_on_main_thread(fake_maya):
    seen: list = []
    assert main_thread_mod.run_on_main_thread(lambda: seen.append(1)) is True
    assert seen == [1]


def test_run_on_main_thread_defers_from_worker(fake_maya):
    cmds, utils = fake_maya
    exc = _run_in_worker(lambda: main_thread_mod.run_on_main_thread(lambda: None))
    assert exc is None
    assert len(utils.deferred) == 1


def test_run_on_main_thread_returns_false_when_deferral_fails(fake_maya):
    """If the hop to the main thread cannot be scheduled, report failure.

    Callers keep their state so a later retry can finish the teardown.
    """
    _cmds, utils = fake_maya

    def _boom(fn, *args, **kwargs):
        raise RuntimeError("maya is shutting down")

    utils.executeDeferred = _boom
    sys.modules["maya.utils"].executeDeferred = _boom

    exc = _run_in_worker(lambda: main_thread_mod.run_on_main_thread(lambda: None))
    assert exc is None, "run_on_main_thread must never raise"

    # Re-run on a worker thread (not inline) to exercise the deferral path.
    results: list = []

    def _capture():
        results.append(main_thread_mod.run_on_main_thread(lambda: None))

    _run_in_worker(_capture)
    assert results == [False]
