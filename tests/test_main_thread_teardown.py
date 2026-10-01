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
    """Stand-in for ``maya.cmds`` that records ``scriptJob`` calls."""

    def __init__(self) -> None:
        self.calls: list = []
        self.refuse_kill = False
        self.kill_raises: type = TypeError

    def scriptJob(self, *args, **kwargs):
        self.calls.append((args, kwargs))
        if "kill" in kwargs:
            if self.refuse_kill:
                raise self.kill_raises("Invalid argument for flag 'kill'. Expected int, got NoneType")
            return None
        return 100 + len(self.calls)


class FakeMayaUtils:
    """Stand-in for ``maya.utils`` capturing deferred callbacks."""

    def __init__(self) -> None:
        self.deferred: list = []

    def executeDeferred(self, fn, *args, **kwargs):
        self.deferred.append(fn)


@pytest.fixture
def fake_maya(monkeypatch):
    """Install fake ``maya``, ``maya.cmds`` and ``maya.utils`` modules."""
    cmds = FakeCmds()
    utils = FakeMayaUtils()

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
