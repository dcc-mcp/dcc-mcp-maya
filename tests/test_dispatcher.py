"""Tests for MayaUiDispatcher, MayaStandaloneDispatcher, and MayaUiPump.

See: https://github.com/loonghao/dcc-mcp-maya/issues/66
"""

# Import future modules
from __future__ import annotations

# Import built-in modules
import sys
import threading
import time
from unittest.mock import MagicMock, patch

# Import third-party modules
import pytest


@pytest.fixture(autouse=True)
def mock_maya_modules():
    """Inject minimal maya stubs so dispatcher can be imported without Maya."""
    maya_mock = MagicMock()
    maya_mock.cmds = MagicMock()
    maya_mock.cmds.about.return_value = "2025"
    maya_mock.cmds.scriptJob.return_value = 42
    maya_mock.mel = MagicMock()
    maya_mock.utils = MagicMock()

    mods = {
        "maya": maya_mock,
        "maya.cmds": maya_mock.cmds,
        "maya.mel": maya_mock.mel,
        "maya.utils": maya_mock.utils,
    }
    with patch.dict(sys.modules, mods):
        yield maya_mock


def _import_fresh():
    """Force reimport of dispatcher module."""
    import importlib

    for mod in list(sys.modules):
        if "dcc_mcp_maya" in mod:
            del sys.modules[mod]
    return importlib.import_module("dcc_mcp_maya.dispatcher")


# ── MayaUiDispatcher tests ───────────────────────────────────────────────────


class TestMayaUiDispatcher:
    """Tests for MayaUiDispatcher."""

    def test_submit_any_affinity_returns_payload(self):
        from dcc_mcp_maya.dispatcher import MayaUiDispatcher

        d = MayaUiDispatcher()
        result = d.submit("test_action", payload="hello", affinity="any")

        assert result["request_id"] == "test_action"
        assert result["affinity"] == "any"
        assert result["success"] is True
        assert result["output"] == "hello"
        assert result["error"] is None

    def test_submit_any_affinity_none_payload(self):
        from dcc_mcp_maya.dispatcher import MayaUiDispatcher

        d = MayaUiDispatcher()
        result = d.submit("test_action", affinity="any")

        assert result["success"] is True
        assert result["output"] is None

    def test_submit_invalid_affinity_returns_error(self):
        from dcc_mcp_maya.dispatcher import MayaUiDispatcher

        d = MayaUiDispatcher()
        result = d.submit("test_action", affinity="named:foo")

        assert result["success"] is False
        assert "Unsupported affinity" in result["error"]

    def test_submit_main_affinity_queues_and_drains(self):
        from dcc_mcp_maya.dispatcher import MayaUiDispatcher

        d = MayaUiDispatcher()

        # Submit from a background thread so it blocks waiting for drain
        result_holder = [None]

        def _worker():
            result_holder[0] = d.submit("main_action", payload="from_main", affinity="main", timeout_ms=5000)

        t = threading.Thread(target=_worker)
        t.start()

        # Give the thread time to enqueue
        time.sleep(0.05)
        assert d.pending_count() >= 1

        # Drain on "main thread"
        executed, remaining = d.drain_queue(budget_ms=100)
        assert executed >= 1

        t.join(timeout=5)
        assert result_holder[0] is not None
        assert result_holder[0]["success"] is True
        assert result_holder[0]["output"] == "from_main"

    def test_submit_callable_main_affinity(self):
        from dcc_mcp_maya.dispatcher import MayaUiDispatcher

        d = MayaUiDispatcher()
        result_holder = [None]

        def _task():
            return {"answer": 42}

        def _worker():
            result_holder[0] = d.submit_callable("callable_main", _task, affinity="main", timeout_ms=5000)

        t = threading.Thread(target=_worker)
        t.start()

        time.sleep(0.05)
        d.drain_queue(budget_ms=100)

        t.join(timeout=5)
        assert result_holder[0] is not None
        assert result_holder[0]["success"] is True
        assert result_holder[0]["output"] == {"answer": 42}

    def test_submit_callable_any_affinity(self):
        from dcc_mcp_maya.dispatcher import MayaUiDispatcher

        d = MayaUiDispatcher()
        result = d.submit_callable("callable_any", lambda: "immediate", affinity="any")

        assert result["success"] is True
        assert result["output"] == "immediate"

    def test_submit_callable_error_handling(self):
        from dcc_mcp_maya.dispatcher import MayaUiDispatcher

        d = MayaUiDispatcher()
        result = d.submit_callable("callable_err", lambda: 1 / 0, affinity="any")

        assert result["success"] is False
        assert "division by zero" in result["error"]

    def test_cancel_pending_job(self):
        from dcc_mcp_maya.dispatcher import MayaUiDispatcher

        d = MayaUiDispatcher()
        result_holder = [None]

        def _worker():
            result_holder[0] = d.submit("cancel_me", payload="x", affinity="main", timeout_ms=5000)

        t = threading.Thread(target=_worker)
        t.start()

        time.sleep(0.05)
        cancelled = d.cancel("cancel_me")
        assert cancelled is True

        t.join(timeout=5)
        assert result_holder[0] is not None
        assert result_holder[0]["success"] is False
        assert result_holder[0]["error"] == "Cancelled"

    def test_cancel_nonexistent_job(self):
        from dcc_mcp_maya.dispatcher import MayaUiDispatcher

        d = MayaUiDispatcher()
        assert d.cancel("no_such_job") is False

    def test_timeout_returns_error(self):
        from dcc_mcp_maya.dispatcher import MayaUiDispatcher

        d = MayaUiDispatcher()
        # Submit with very short timeout and never drain
        result = d.submit("timeout_action", payload="x", affinity="main", timeout_ms=50)

        assert result["success"] is False
        assert "Timeout" in result["error"]

    def test_supported_returns_both_affinities(self):
        from dcc_mcp_maya.dispatcher import MayaUiDispatcher

        d = MayaUiDispatcher()
        assert set(d.supported()) == {"any", "main"}

    def test_capabilities_flags(self):
        from dcc_mcp_maya.dispatcher import MayaUiDispatcher

        d = MayaUiDispatcher()
        caps = d.capabilities()

        assert caps["supports_main_thread"] is True
        assert caps["supports_any_thread"] is True
        assert caps["supports_time_slicing"] is True
        assert caps["supports_named_threads"] is False

    def test_pending_count_starts_at_zero(self):
        from dcc_mcp_maya.dispatcher import MayaUiDispatcher

        d = MayaUiDispatcher()
        assert d.pending_count() == 0

    def test_drain_empty_queue(self):
        from dcc_mcp_maya.dispatcher import MayaUiDispatcher

        d = MayaUiDispatcher()
        executed, remaining = d.drain_queue(budget_ms=10)
        assert executed == 0
        assert remaining == 0

    def test_drain_respects_budget(self):
        """Verify that the pump yields after budget is exhausted."""
        from dcc_mcp_maya.dispatcher import MayaUiDispatcher

        d = MayaUiDispatcher()

        # Enqueue many slow jobs
        for i in range(20):
            job_result = [None]

            def _slow_task(idx=i):
                time.sleep(0.005)  # 5ms each
                return f"job_{idx}"

            def _worker(idx=i):
                job_result[0] = d.submit_callable(f"slow_{idx}", _slow_task, affinity="main", timeout_ms=10000)

            t = threading.Thread(target=_worker)
            t.start()

        time.sleep(0.1)  # Let all threads enqueue

        # Drain with 15ms budget — should execute only ~2-3 jobs
        executed, remaining = d.drain_queue(budget_ms=15)
        assert executed < 20  # Didn't drain all
        assert remaining > 0  # Some still pending

    def test_concurrent_submit_safety(self):
        """Multiple threads submitting simultaneously should not crash."""
        from dcc_mcp_maya.dispatcher import MayaUiDispatcher

        d = MayaUiDispatcher()
        results = []
        errors = []

        def _submit(idx):
            try:
                r = d.submit(f"concurrent_{idx}", payload=str(idx), affinity="any")
                results.append(r)
            except Exception as exc:
                errors.append(exc)

        threads = [threading.Thread(target=_submit, args=(i,)) for i in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=5)

        assert len(errors) == 0
        assert len(results) == 10
        assert all(r["success"] for r in results)

    # ── BaseDccCallableDispatcher protocol (issue #136) ───────────────────────

    def test_dispatch_callable_routes_to_main_thread(self):
        """``dispatch_callable`` must enqueue on the main queue and block."""
        from dcc_mcp_maya.dispatcher import MayaUiDispatcher

        d = MayaUiDispatcher()
        result_holder = [None]
        error_holder = [None]

        def _runner(script_path, params):
            return {"script": script_path, "params": dict(params)}

        def _worker():
            try:
                result_holder[0] = d.dispatch_callable(_runner, "skills/foo/scripts/bar.py", {"x": 1})
            except Exception as exc:  # noqa: BLE001
                error_holder[0] = exc

        t = threading.Thread(target=_worker)
        t.start()

        # Give the worker a chance to enqueue, then drain on this thread.
        # Poll for up to 1s — Windows scheduling can be slower than 50ms.
        deadline = time.monotonic() + 1.0
        while d.pending_count() == 0 and time.monotonic() < deadline:
            time.sleep(0.01)
        assert d.pending_count() >= 1, f"worker error: {error_holder[0]!r}"
        d.drain_queue(budget_ms=100)

        t.join(timeout=5)
        assert error_holder[0] is None, error_holder[0]
        assert result_holder[0] == {
            "script": "skills/foo/scripts/bar.py",
            "params": {"x": 1},
        }

    def test_dispatch_callable_propagates_exceptions(self):
        """Exceptions raised in *func* must surface from ``dispatch_callable``."""
        from dcc_mcp_maya.dispatcher import MayaUiDispatcher

        d = MayaUiDispatcher()
        captured = [None]

        def _bad(*_a, **_kw):
            raise ValueError("boom")

        def _worker():
            try:
                d.dispatch_callable(_bad)
            except Exception as exc:  # noqa: BLE001
                captured[0] = exc

        t = threading.Thread(target=_worker)
        t.start()
        deadline = time.monotonic() + 1.0
        while d.pending_count() == 0 and time.monotonic() < deadline:
            time.sleep(0.01)
        d.drain_queue(budget_ms=100)
        t.join(timeout=5)

        assert captured[0] is not None
        assert "boom" in str(captured[0])

    def test_dispatch_callable_satisfies_protocol(self):
        """:class:`MayaUiDispatcher` must satisfy ``BaseDccCallableDispatcher``.

        Regression for issue #136: without this, ``HostExecutionBridge``
        cannot route ``affinity: main`` tools through the UI thread.
        """
        from dcc_mcp_maya.dispatcher import MayaUiDispatcher

        d = MayaUiDispatcher()
        assert hasattr(d, "dispatch_callable")
        assert callable(d.dispatch_callable)

        from dcc_mcp_core._server.inprocess_executor import (
            BaseDccCallableDispatcher,
        )

        if sys.version_info < (3, 8):
            pytest.skip("Python 3.7 Protocol runtime checks differ from typing_extensions")
        assert isinstance(d, BaseDccCallableDispatcher)


# ── MayaStandaloneDispatcher tests ───────────────────────────────────────────


class TestMayaStandaloneDispatcher:
    """Tests for MayaStandaloneDispatcher."""

    def test_submit_returns_payload(self):
        from dcc_mcp_maya.dispatcher import MayaStandaloneDispatcher

        d = MayaStandaloneDispatcher()
        result = d.submit("test", payload="hello")

        assert result["success"] is True
        assert result["output"] == "hello"

    def test_submit_ignores_affinity(self):
        from dcc_mcp_maya.dispatcher import MayaStandaloneDispatcher

        d = MayaStandaloneDispatcher()
        # Main affinity should work in standalone (no thread restriction)
        result = d.submit("test", payload="main_ok", affinity="main")

        assert result["success"] is True
        assert result["output"] == "main_ok"

    def test_submit_callable_success(self):
        from dcc_mcp_maya.dispatcher import MayaStandaloneDispatcher

        d = MayaStandaloneDispatcher()
        result = d.submit_callable("task", lambda: {"x": 1})

        assert result["success"] is True
        assert result["output"] == {"x": 1}

    def test_submit_callable_error(self):
        from dcc_mcp_maya.dispatcher import MayaStandaloneDispatcher

        d = MayaStandaloneDispatcher()
        result = d.submit_callable("err_task", lambda: 1 / 0)

        assert result["success"] is False
        assert "division by zero" in result["error"]

    def test_dispatch_callable_satisfies_core_protocol(self):
        from dcc_mcp_maya.dispatcher import MayaStandaloneDispatcher

        d = MayaStandaloneDispatcher()
        result = d.dispatch_callable(
            lambda value: {"value": value},
            42,
            affinity="main",
            action_name="maya_primitives__create_sphere",
            timeout_hint_secs=30,
        )

        assert result == {"value": 42}
        assert hasattr(d, "dispatch_callable")
        assert callable(d.dispatch_callable)

        from dcc_mcp_core._server.inprocess_executor import (
            BaseDccCallableDispatcher,
        )

        if sys.version_info < (3, 8):
            pytest.skip("Python 3.7 Protocol runtime checks differ from typing_extensions")
        assert isinstance(d, BaseDccCallableDispatcher)

    def test_supported(self):
        from dcc_mcp_maya.dispatcher import MayaStandaloneDispatcher

        d = MayaStandaloneDispatcher()
        assert set(d.supported()) == {"any", "main"}

    def test_capabilities_no_time_slicing(self):
        from dcc_mcp_maya.dispatcher import MayaStandaloneDispatcher

        d = MayaStandaloneDispatcher()
        caps = d.capabilities()
        assert caps["supports_time_slicing"] is False
        assert caps["supports_main_thread"] is True


# ── MayaUiPump tests ────────────────────────────────────────────────────────


class TestMayaUiPump:
    """Tests for MayaUiPump."""

    def test_install_registers_scriptjob(self, mock_maya_modules):
        from dcc_mcp_maya.dispatcher import MayaUiDispatcher, MayaUiPump

        d = MayaUiDispatcher()
        pump = MayaUiPump(d, budget_ms=8)

        result = pump.install()
        assert result is True
        assert pump.is_installed is True
        mock_maya_modules.cmds.scriptJob.assert_called_once()

    def test_install_is_idempotent(self, mock_maya_modules):
        from dcc_mcp_maya.dispatcher import MayaUiDispatcher, MayaUiPump

        d = MayaUiDispatcher()
        pump = MayaUiPump(d, budget_ms=8)

        pump.install()
        pump.install()  # second call should be no-op
        assert mock_maya_modules.cmds.scriptJob.call_count == 1

    def test_uninstall_removes_scriptjob(self, mock_maya_modules):
        from dcc_mcp_maya.dispatcher import MayaUiDispatcher, MayaUiPump

        d = MayaUiDispatcher()
        pump = MayaUiPump(d, budget_ms=8)

        pump.install()
        pump.uninstall()

        assert pump.is_installed is False
        mock_maya_modules.cmds.scriptJob.assert_any_call(kill=42, force=True)

    def test_uninstall_when_not_installed(self):
        from dcc_mcp_maya.dispatcher import MayaUiDispatcher, MayaUiPump

        d = MayaUiDispatcher()
        pump = MayaUiPump(d)

        # Should be a no-op
        pump.uninstall()
        assert pump.is_installed is False

    def test_budget_ms_property(self):
        from dcc_mcp_maya.dispatcher import MayaUiDispatcher, MayaUiPump

        d = MayaUiDispatcher()
        pump = MayaUiPump(d, budget_ms=16)

        assert pump.budget_ms == 16
        pump.budget_ms = 4
        assert pump.budget_ms == 4

    def test_budget_ms_floor(self):
        from dcc_mcp_maya.dispatcher import MayaUiDispatcher, MayaUiPump

        d = MayaUiDispatcher()
        pump = MayaUiPump(d)
        pump.budget_ms = 0.1
        assert pump.budget_ms == 1.0

    def test_stats_tracking(self):
        from dcc_mcp_maya.dispatcher import MayaUiDispatcher, MayaUiPump

        d = MayaUiDispatcher()
        pump = MayaUiPump(d, budget_ms=50)

        # Simulate a pump tick with an empty queue
        pump._pump_tick()

        stats = pump.stats
        assert stats["total_cycles"] == 1
        assert stats["total_executed"] == 0

    def test_pump_tick_drains_jobs(self):
        from dcc_mcp_maya.dispatcher import MayaUiDispatcher, MayaUiPump

        d = MayaUiDispatcher()
        pump = MayaUiPump(d, budget_ms=100)

        result_holder = [None]

        def _worker():
            result_holder[0] = d.submit("pumped_job", payload="data", affinity="main", timeout_ms=5000)

        t = threading.Thread(target=_worker)
        t.start()
        time.sleep(0.05)

        pump._pump_tick()

        t.join(timeout=5)
        assert result_holder[0] is not None
        assert result_holder[0]["success"] is True
        assert result_holder[0]["output"] == "data"

        stats = pump.stats
        assert stats["total_executed"] >= 1


# ── create_dispatcher factory tests ──────────────────────────────────────────


class TestCreateDispatcher:
    """Tests for the create_dispatcher factory."""

    def test_interactive_returns_ui_dispatcher(self, mock_maya_modules):
        mock_maya_modules.cmds.about.return_value = False  # not batch

        from dcc_mcp_maya.dispatcher import MayaUiDispatcher, MayaUiPump, create_dispatcher

        dispatcher, pump = create_dispatcher()
        assert isinstance(dispatcher, MayaUiDispatcher)
        assert isinstance(pump, MayaUiPump)

    def test_batch_returns_standalone_dispatcher(self, mock_maya_modules):
        mock_maya_modules.cmds.about.return_value = True  # batch mode

        from dcc_mcp_maya.dispatcher import MayaStandaloneDispatcher, create_dispatcher

        dispatcher, pump = create_dispatcher()
        assert isinstance(dispatcher, MayaStandaloneDispatcher)
        assert pump is None

    def test_no_maya_returns_standalone_dispatcher(self):
        with patch.dict(sys.modules, {"maya": None, "maya.cmds": None}):
            mod = _import_fresh()
            # Can't import maya.cmds → falls back to standalone
            # The ImportError from maya.cmds triggers batch path
            dispatcher, pump = mod.create_dispatcher()
            assert isinstance(dispatcher, mod.MayaStandaloneDispatcher)
            assert pump is None


# ── Integration: dispatcher + pump round-trip ─────────────────────────────────


class TestDispatcherPumpIntegration:
    """Integration tests for dispatcher + pump working together."""

    def test_full_round_trip(self):
        """Submit from background, pump on main, result received."""
        from dcc_mcp_maya.dispatcher import MayaUiDispatcher, MayaUiPump

        d = MayaUiDispatcher()
        pump = MayaUiPump(d, budget_ms=50)

        results = []

        def _worker(idx):
            r = d.submit(f"rt_{idx}", payload=f"payload_{idx}", affinity="main", timeout_ms=5000)
            results.append(r)

        threads = [threading.Thread(target=_worker, args=(i,)) for i in range(5)]
        for t in threads:
            t.start()

        time.sleep(0.1)

        # Simulate several pump ticks
        for _ in range(10):
            pump._pump_tick()
            if d.pending_count() == 0:
                break
            time.sleep(0.01)

        for t in threads:
            t.join(timeout=5)

        assert len(results) == 5
        assert all(r["success"] for r in results)

    def test_cancel_during_pump(self):
        """Cancel a job before the pump gets to it."""
        from dcc_mcp_maya.dispatcher import MayaUiDispatcher, MayaUiPump

        d = MayaUiDispatcher()
        pump = MayaUiPump(d, budget_ms=50)  # noqa: F841 — keep reference

        result_holder = [None]

        def _worker():
            result_holder[0] = d.submit("cancel_target", payload="x", affinity="main", timeout_ms=5000)

        t = threading.Thread(target=_worker)
        t.start()
        time.sleep(0.05)

        d.cancel("cancel_target")

        t.join(timeout=5)
        assert result_holder[0] is not None
        assert result_holder[0]["success"] is False
        assert result_holder[0]["error"] == "Cancelled"
