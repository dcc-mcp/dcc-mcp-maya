"""Tests for the universal main-thread safety net in :mod:`dcc_mcp_maya._executor`.

What this guards
================

Every skill action dispatched through the MCP HTTP server runs through
:func:`dcc_mcp_maya._executor.execute_in_process`. The routing it does
combines the ``tools.yaml`` ``affinity`` field with the current thread
context. The user-facing contract is:

* ``affinity: any``  → run inline on the calling thread.
* ``affinity: main`` + already on main thread → inline.
* ``affinity: main`` + worker thread + dispatcher attached → dispatcher.
* ``affinity: main`` + worker thread + **no** dispatcher → main-thread
  queue (the safety net).

Before the safety net existed, the last row ran the action inline on a
hyper / tokio worker thread. Calling ``maya.cmds.*`` from there crashes
Maya — verified in #248 against the user's batch FBX script. The queue
collapses that case to ``maya.utils.executeInMainThreadWithResult`` so
Maya keeps running.

Test strategy: monkey-patch ``_affinity.resolve_affinity`` so we don't
need real ``tools.yaml`` on disk, monkey-patch ``_running_on_main_thread``
to simulate the worker / main contexts, and verify the dispatch route
each path takes.
"""

# Import future modules
from __future__ import annotations

# Import built-in modules
from typing import Any, Dict
from unittest.mock import MagicMock

# Import third-party modules
import pytest

# Import local modules
from dcc_mcp_maya import _affinity, _executor, _main_thread_queue


@pytest.fixture(autouse=True)
def _reset_queue_singleton():
    _main_thread_queue.reset_for_tests()
    _executor._recovery_dialog.reset_for_tests()
    yield
    _executor._recovery_dialog.reset_for_tests()
    _main_thread_queue.reset_for_tests()


@pytest.fixture
def fake_script(tmp_path):
    """Minimal skill script that records that it ran and returns a known envelope."""
    script = tmp_path / "scripts" / "fake.py"
    script.parent.mkdir(parents=True, exist_ok=True)
    script.write_text(
        "import threading\n"
        "_THREAD_NAME = []\n"
        "def main(**kwargs):\n"
        "    _THREAD_NAME.append(threading.current_thread().name)\n"
        "    return {'success': True, 'message': 'ran', 'context': {'thread': _THREAD_NAME[-1], 'kwargs': kwargs}}\n",
        encoding="utf-8",
    )
    return str(script)


class TestAffinityAnyAlwaysInline:
    """``affinity: any`` must skip every marshalling path."""

    def test_runs_inline_even_with_dispatcher_present(self, fake_script, monkeypatch):
        monkeypatch.setattr(_affinity, "resolve_affinity", lambda _p: "any")
        monkeypatch.setattr(_executor, "_on_main_thread", lambda: False)

        dispatcher = MagicMock()
        server = MagicMock(_maya_dispatcher=dispatcher)

        out = _executor.execute_in_process(server, fake_script, {"foo": "bar"}, "fake__main")

        assert out["success"] is True
        # affinity=any must NOT touch the dispatcher.
        dispatcher.submit_callable.assert_not_called()
        # And must NOT touch the queue either.
        assert _main_thread_queue.get_queue().status()["submitted"] == 0

    def test_skips_recovery_dialog_poll(self, fake_script, monkeypatch):
        monkeypatch.setattr(_affinity, "resolve_affinity", lambda _p: "any")
        monkeypatch.setattr(_executor, "_on_main_thread", lambda: False)

        def fail_poll(_result):
            raise AssertionError("affinity:any must not poll Qt dialogs")

        monkeypatch.setattr(_executor._recovery_dialog, "poll_and_annotate_result", fail_poll)

        out = _executor.execute_in_process(MagicMock(spec=[]), fake_script, {}, "fake__main")

        assert out["success"] is True


class TestAffinityMainOnMainThreadInline:
    """``affinity: main`` + already on main thread → inline (no deadlock)."""

    def test_on_main_thread_runs_inline_skipping_marshalling(self, fake_script, monkeypatch):
        monkeypatch.setattr(_affinity, "resolve_affinity", lambda _p: "main")
        monkeypatch.setattr(_executor, "_on_main_thread", lambda: True)

        dispatcher = MagicMock()
        server = MagicMock(_maya_dispatcher=dispatcher)

        out = _executor.execute_in_process(server, fake_script, {}, "fake__main")

        assert out["success"] is True
        # Already on main: dispatcher / queue would deadlock — neither must be used.
        dispatcher.submit_callable.assert_not_called()
        assert _main_thread_queue.get_queue().status()["submitted"] == 0


class TestAffinityMainOffMainWithDispatcher:
    """``affinity: main`` + worker thread + dispatcher attached → dispatcher path."""

    def test_dispatcher_submit_callable_invoked_with_main_affinity(self, fake_script, monkeypatch):
        monkeypatch.setattr(_affinity, "resolve_affinity", lambda _p: "main")
        monkeypatch.setattr(_executor, "_on_main_thread", lambda: False)

        captured: Dict[str, Any] = {}

        def fake_submit_callable(request_id: str, task, affinity: str = "main", **kw):
            captured["request_id"] = request_id
            captured["affinity"] = affinity
            return {"success": True, "output": task()}

        dispatcher = MagicMock()
        dispatcher.submit_callable = fake_submit_callable
        server = MagicMock(_maya_dispatcher=dispatcher)

        out = _executor.execute_in_process(server, fake_script, {}, "fake__main")

        assert out["success"] is True
        assert captured["affinity"] == "main"
        assert captured["request_id"] == "fake__main"
        # Safety-net queue must NOT have been touched when dispatcher is healthy.
        assert _main_thread_queue.get_queue().status()["submitted"] == 0

    def test_dispatcher_path_polls_recovery_dialog_inside_callable(self, fake_script, monkeypatch):
        monkeypatch.setattr(_affinity, "resolve_affinity", lambda _p: "main")
        monkeypatch.setattr(_executor, "_on_main_thread", lambda: False)

        calls = []

        def fake_poll(result):
            calls.append(result)
            out = dict(result)
            context = dict(out.get("context") or {})
            context["maya_status"] = "recovery_dialog_detected"
            out["context"] = context
            return out

        def fake_submit_callable(_request_id: str, task, affinity: str = "main", **_kw):
            assert affinity == "main"
            return {"success": True, "output": task()}

        monkeypatch.setattr(_executor._recovery_dialog, "poll_and_annotate_result", fake_poll)
        dispatcher = MagicMock()
        dispatcher.submit_callable = fake_submit_callable
        server = MagicMock(_maya_dispatcher=dispatcher)

        out = _executor.execute_in_process(server, fake_script, {}, "fake__main")

        assert len(calls) == 1
        assert out["success"] is True
        assert out["context"]["maya_status"] == "recovery_dialog_detected"

    def test_dispatcher_exception_becomes_structured_envelope(self, fake_script, monkeypatch):
        monkeypatch.setattr(_affinity, "resolve_affinity", lambda _p: "main")
        monkeypatch.setattr(_executor, "_on_main_thread", lambda: False)

        dispatcher = MagicMock()
        dispatcher.submit_callable.side_effect = RuntimeError("dispatcher died")
        server = MagicMock(_maya_dispatcher=dispatcher)

        out = _executor.execute_in_process(server, fake_script, {}, "fake__main")

        assert out["success"] is False
        # Dispatcher failure must not bubble as an internal error — it must
        # become a structured skill_exception envelope.
        assert "Dispatcher failed" in (out.get("message") or "")


class TestSafetyNetWhenNoDispatcher:
    """``affinity: main`` + worker thread + **no** dispatcher → main-thread queue."""

    def test_no_dispatcher_routes_through_queue(self, fake_script, monkeypatch):
        monkeypatch.setattr(_affinity, "resolve_affinity", lambda _p: "main")
        monkeypatch.setattr(_executor, "_on_main_thread", lambda: False)

        # No Maya bridge in this test — the queue pump falls back to inline
        # so we can verify the queue path without standing up Maya.
        monkeypatch.setattr(_main_thread_queue, "_import_maya_utils", lambda: None)

        # Crucially: no _maya_dispatcher attribute on the server.
        server = MagicMock(spec=[])

        out = _executor.execute_in_process(server, fake_script, {"k": "v"}, "fake__main")

        assert out["success"] is True
        # Queue MUST have been used.
        status = _main_thread_queue.get_queue().status()
        assert status["submitted"] >= 1
        assert status["completed"] >= 1

    def test_dispatcher_without_submit_callable_falls_back_to_queue(self, fake_script, monkeypatch):
        """A duck-typed dispatcher missing ``submit_callable`` must trigger the safety net."""
        monkeypatch.setattr(_affinity, "resolve_affinity", lambda _p: "main")
        monkeypatch.setattr(_executor, "_on_main_thread", lambda: False)
        monkeypatch.setattr(_main_thread_queue, "_import_maya_utils", lambda: None)

        # Use object() so MagicMock's auto-spec doesn't accidentally supply
        # a submit_callable attribute.
        class _PartialDispatcher:
            """Some custom dispatcher implementation that doesn't speak our API."""

        server = MagicMock(_maya_dispatcher=_PartialDispatcher())

        out = _executor.execute_in_process(server, fake_script, {}, "fake__main")

        assert out["success"] is True
        assert _main_thread_queue.get_queue().status()["submitted"] >= 1

    def test_queue_full_returns_backpressure_envelope(self, fake_script, monkeypatch):
        """When the safety-net queue is full, the agent gets a clean envelope."""
        from concurrent.futures import Future

        monkeypatch.setattr(_affinity, "resolve_affinity", lambda _p: "main")
        monkeypatch.setattr(_executor, "_on_main_thread", lambda: False)

        full_future: Future = Future()
        full_future.set_exception(_main_thread_queue.QueueFullError("Queue is at depth 64; back off."))

        fake_queue = MagicMock()
        fake_queue.submit.return_value = full_future
        monkeypatch.setattr(_main_thread_queue, "get_queue", lambda: fake_queue)

        server = MagicMock(spec=[])

        out = _executor.execute_in_process(server, fake_script, {}, "fake__main")

        assert out["success"] is False
        joined = (out.get("message") or "") + "\n" + str(out.get("context") or "")
        assert "queue is full" in joined.lower() or "back off" in joined.lower()


class TestEveryDeclaredAffinityHonoured:
    """Sanity sweep: every skill action's declared affinity drives the route.

    This is the integration-level guard for the user's request — every
    Maya skill that touches ``cmds.*`` is tagged ``affinity: main`` in
    its ``tools.yaml``; that declaration must not silently degrade into
    inline worker-thread execution.
    """

    def test_main_affinity_skills_never_run_inline_off_main(self, tmp_path, monkeypatch):
        """Simulate two skills (one ``main``, one ``any``) and verify routing."""
        # Two fake skills sharing the same parent so the tools.yaml lookup works.
        skill_root = tmp_path / "fake-skill"
        (skill_root / "scripts").mkdir(parents=True)

        # ``cmds_action`` declares affinity: main → must marshal.
        # ``pure_action`` declares affinity: any  → must run inline.
        (skill_root / "scripts" / "cmds_action.py").write_text(
            "def main(**kw): return {'success': True, 'message': 'cmds'}\n",
            encoding="utf-8",
        )
        (skill_root / "scripts" / "pure_action.py").write_text(
            "def main(**kw): return {'success': True, 'message': 'pure'}\n",
            encoding="utf-8",
        )
        (skill_root / "tools.yaml").write_text(
            "tools:\n"
            "- name: cmds_action\n"
            "  affinity: main\n"
            "  execution: sync\n"
            "- name: pure_action\n"
            "  affinity: any\n"
            "  execution: sync\n",
            encoding="utf-8",
        )

        _affinity.clear_cache()
        monkeypatch.setattr(_executor, "_on_main_thread", lambda: False)
        monkeypatch.setattr(_main_thread_queue, "_import_maya_utils", lambda: None)

        server = MagicMock(spec=[])  # no dispatcher → safety net engaged

        # main-affinity action goes through the queue.
        out_main = _executor.execute_in_process(
            server, str(skill_root / "scripts" / "cmds_action.py"), {}, "fake__cmds"
        )
        assert out_main["success"] is True
        q_after_main = _main_thread_queue.get_queue().status()["submitted"]
        assert q_after_main == 1, "main-affinity action must route through queue, status was {0}".format(q_after_main)

        # any-affinity action stays on the worker thread.
        out_any = _executor.execute_in_process(server, str(skill_root / "scripts" / "pure_action.py"), {}, "fake__pure")
        assert out_any["success"] is True
        q_after_any = _main_thread_queue.get_queue().status()["submitted"]
        assert q_after_any == q_after_main, "any-affinity action must NOT touch the queue"
