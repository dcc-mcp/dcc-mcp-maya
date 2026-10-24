"""Tests for the MayaHost core HostAdapter implementation."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

_SRC = Path(__file__).parents[1] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))


def _install_maya(cmds):
    maya = MagicMock()
    maya.cmds = cmds
    return patch.dict(sys.modules, {"maya": maya, "maya.cmds": cmds})


class _Dispatcher:
    def __init__(self):
        self.shutdown_called = False

    def tick(self, _max_jobs):
        return MagicMock(more_pending=False)

    def is_shutdown(self):
        return self.shutdown_called

    def shutdown(self):
        self.shutdown_called = True


def test_is_background_uses_maya_batch_flag():
    from dcc_mcp_maya.host import MayaHost

    cmds = MagicMock()
    cmds.about.return_value = False
    with _install_maya(cmds):
        assert MayaHost(_Dispatcher()).is_background() is False
    cmds.about.assert_called_once_with(batch=True)


@pytest.fixture(params=["PySide6", "PySide2"])
def host_qt(watchdog_qt, monkeypatch, request):
    if request.param == "PySide2":
        monkeypatch.setitem(sys.modules, "PySide2", sys.modules["PySide6"])
        monkeypatch.setitem(sys.modules, "PySide2.QtCore", sys.modules["PySide6.QtCore"])
        monkeypatch.setitem(sys.modules, "PySide6", None)
        monkeypatch.setitem(sys.modules, "PySide6.QtCore", None)
    with _install_maya(MagicMock()):
        yield watchdog_qt


def test_tick_honours_core_intervals_and_stops(host_qt):
    from dcc_mcp_maya.host import MayaHost

    host = MayaHost(_Dispatcher())
    tick = MagicMock(side_effect=[0.5, 0.0, 0.125, None])
    host.attach_tick(tick)
    assert len(host_qt) == 1
    timer = host_qt[0]
    assert timer.single_shot and timer.interval == 0
    for delay in (500, 0, 125):
        timer.fire()
        assert timer.active and timer.interval == delay
    timer.fire()
    assert timer.deleted and not timer.active
    assert tick.call_count == 4


def test_detach_and_reattach_ignore_late_callbacks(host_qt):
    from dcc_mcp_maya.host import MayaHost

    host = MayaHost(_Dispatcher())
    tick = MagicMock(return_value=0.5)
    host.attach_tick(tick)
    host.attach_tick(tick)
    assert len(host_qt) == 1
    old = host_qt[0]
    host.detach_tick()
    host.detach_tick()
    assert old.deleted and not old.active
    host.attach_tick(tick)
    old.fire()
    tick.assert_not_called()
    host_qt[1].fire()
    tick.assert_called_once_with()
    host.detach_tick()


def test_detach_during_tick_does_not_rearm(host_qt):
    from dcc_mcp_maya.host import MayaHost

    host = MayaHost(_Dispatcher())
    host.attach_tick(lambda: (host.detach_tick(), 0.5)[1])
    host_qt[0].fire()
    assert host_qt[0].deleted and not host_qt[0].active


def test_core_tick_drains_then_sleeps_and_stops(host_qt):
    from dcc_mcp_maya.host import MayaHost

    dispatcher = _Dispatcher()
    dispatcher.tick = MagicMock(side_effect=[MagicMock(more_pending=True), MagicMock(more_pending=False)])
    host = MayaHost(dispatcher)
    host.attach_tick(host._tick)
    timer = host_qt[0]
    timer.fire()
    assert timer.interval == 0
    timer.fire()
    assert timer.interval == 500
    dispatcher.shutdown()
    timer.fire()
    assert timer.deleted and not timer.active
    assert dispatcher.tick.call_count == 2


def test_tick_error_releases_timer(host_qt):
    from dcc_mcp_maya.host import MayaHost

    host = MayaHost(_Dispatcher())
    host.attach_tick(MagicMock(side_effect=RuntimeError("dispatch failed")))
    with pytest.raises(RuntimeError, match="dispatch failed"):
        host_qt[0].fire()
    assert host_qt[0].deleted and not host_qt[0].active
    assert host._tick_timer is None


def test_host_tick_rejects_worker_thread(host_qt):
    from concurrent.futures import ThreadPoolExecutor

    from dcc_mcp_maya.host import MayaHost

    host = MayaHost(_Dispatcher())
    tick = MagicMock(return_value=0.5)
    with ThreadPoolExecutor(max_workers=1) as pool:
        with pytest.raises(RuntimeError, match="main thread"):
            pool.submit(host.attach_tick, tick).result()
        host.attach_tick(tick)
        with pytest.raises(RuntimeError, match="main thread"):
            pool.submit(host_qt[0].fire).result()
        with pytest.raises(RuntimeError, match="main thread"):
            pool.submit(host.detach_tick).result()
    tick.assert_not_called()
    host.detach_tick()


def test_instances_do_not_detach_each_other(host_qt):
    from dcc_mcp_maya.host import MayaHost

    first, second = MayaHost(_Dispatcher()), MayaHost(_Dispatcher())
    first_tick, second_tick = MagicMock(return_value=0.5), MagicMock(return_value=0.5)
    first.attach_tick(first_tick)
    second.attach_tick(second_tick)
    first.detach_tick()
    host_qt[0].fire()
    host_qt[1].fire()
    first_tick.assert_not_called()
    second_tick.assert_called_once_with()
    assert host_qt[1].active
    second.detach_tick()


def test_reattach_during_tick_does_not_rearm_retired_timer(host_qt):
    from dcc_mcp_maya.host import MayaHost

    host = MayaHost(_Dispatcher())
    replacement = MagicMock(return_value=0.5)

    def replace():
        host.detach_tick()
        host.attach_tick(replacement)
        return 0.5

    host.attach_tick(replace)
    host_qt[0].fire()
    assert host_qt[0].deleted and not host_qt[0].active
    host_qt[0].fire()
    replacement.assert_not_called()
    host_qt[1].fire()
    replacement.assert_called_once_with()
    host.detach_tick()


def test_callable_dispatcher_forwards_core_metadata():
    from dcc_mcp_maya.host import MayaCallableDispatcher

    dispatcher = MagicMock()
    bridge = MayaCallableDispatcher(dispatcher)
    fn = MagicMock(return_value={"ok": True})

    context = object()
    result = bridge.dispatch_callable(fn, affinity="main", action_name="maya__tool", context=context)

    assert result == {"ok": True}
    fn.assert_called_once_with(affinity="main", action_name="maya__tool", context=context)
    dispatcher.post.assert_not_called()
