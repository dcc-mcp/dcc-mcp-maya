"""Tests for the MayaHost core HostAdapter implementation."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

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


def test_attach_tick_registers_idle_script_job_and_invokes_tick():
    from dcc_mcp_maya.host import MayaHost

    cmds = MagicMock()
    callbacks = []

    def script_job(**kwargs):
        callbacks.append(kwargs["idleEvent"])
        return 42

    cmds.scriptJob.side_effect = script_job
    with _install_maya(cmds):
        host = MayaHost(_Dispatcher())
        tick = MagicMock(return_value=0.5)
        host.attach_tick(tick)
        callbacks[0]()

    tick.assert_called_once_with()
    assert host._script_job == 42


def test_detach_tick_kills_existing_script_job_and_is_idempotent():
    from dcc_mcp_maya.host import MayaHost

    cmds = MagicMock()
    cmds.scriptJob.side_effect = lambda **kwargs: True if kwargs.get("exists") == 42 else None
    with _install_maya(cmds):
        host = MayaHost(_Dispatcher())
        host._script_job = 42
        host.detach_tick()
        host.detach_tick()

    cmds.scriptJob.assert_any_call(exists=42)
    cmds.scriptJob.assert_any_call(kill=42)
    assert host._script_job is None


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
