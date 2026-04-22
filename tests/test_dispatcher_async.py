"""Tests for ``MayaUiDispatcher.submit_async_callable`` (issue #85).

These tests verify the async dispatch path satisfies the acceptance criteria:

* ``submit_async_callable`` returns in < 50 ms regardless of job duration.
* The returned envelope carries ``status="pending"`` and ``job_id``.
* ``on_complete`` callback is invoked with the final outcome once the job
  executes.
* ``progress_token`` is stored on the queued ``_JobEntry``.
* Shutdown after async enqueue returns an interrupted envelope.
* ``MayaStandaloneDispatcher.submit_async_callable`` executes synchronously
  and calls ``on_complete`` before returning.
"""

from __future__ import annotations

import threading
import time

from dcc_mcp_maya.dispatcher import (
    MayaStandaloneDispatcher,
    MayaUiDispatcher,
)

# ── MayaUiDispatcher async tests ──────────────────────────────────────────────


class TestSubmitAsyncCallable:
    """submit_async_callable returns immediately (issue #85 §2)."""

    def setup_method(self):
        self.dispatcher = MayaUiDispatcher()

    def _drain(self, budget_ms: float = 200) -> None:
        """Helper: drain the UI queue directly (simulates MayaUiPump)."""
        self.dispatcher.drain_queue(budget_ms)

    def test_returns_pending_immediately(self):
        """Envelope is returned before the job executes."""
        started = threading.Event()
        finished = threading.Event()

        def slow_task():
            started.set()
            time.sleep(0.1)
            finished.set()
            return "done"

        t0 = time.monotonic()
        result = self.dispatcher.submit_async_callable("req-1", slow_task, job_id="jid-1")
        elapsed_ms = (time.monotonic() - t0) * 1000

        # Must return before the task runs
        assert elapsed_ms < 50, f"took {elapsed_ms:.1f} ms — expected < 50 ms"
        assert result["status"] == "pending"
        assert result["job_id"] == "jid-1"
        assert result["request_id"] == "req-1"

        # Clean up — drain so the pump thread doesn't linger
        self._drain()

    def test_on_complete_called_after_execution(self):
        """on_complete receives the outcome dict after the job executes."""
        outcomes = []
        done_event = threading.Event()

        def task():
            return 42

        def on_complete(outcome):
            outcomes.append(outcome)
            done_event.set()

        self.dispatcher.submit_async_callable(
            "req-2", task, job_id="jid-2", on_complete=on_complete
        )
        self._drain(budget_ms=200)
        assert done_event.wait(timeout=2.0), "on_complete was never called"

        assert len(outcomes) == 1
        assert outcomes[0]["success"] is True
        assert outcomes[0]["output"] == 42
        assert outcomes[0]["job_id"] == "jid-2"
        assert outcomes[0]["request_id"] == "req-2"

    def test_progress_token_stored_on_job_entry(self):
        """progress_token is attached to the queued _JobEntry."""
        progress_tokens_seen = []
        done = threading.Event()

        def task():
            from dcc_mcp_maya.dispatcher import _current_job

            job = _current_job.get()
            if job is not None:
                progress_tokens_seen.append(job.progress_token)
            done.set()
            return None

        self.dispatcher.submit_async_callable(
            "req-3",
            task,
            progress_token="tok-abc",
        )
        self._drain()
        assert done.wait(1.0), "task never executed"
        assert progress_tokens_seen == ["tok-abc"]

    def test_job_id_propagated_to_outcome(self):
        """job_id from the pending envelope matches the completed outcome."""
        outcome_ref = []
        done = threading.Event()

        def on_complete(outcome):
            outcome_ref.append(outcome)
            done.set()

        self.dispatcher.submit_async_callable(
            "req-4", lambda: "result", job_id="uuid-xyz", on_complete=on_complete
        )
        self._drain()
        assert done.wait(1.0)
        assert outcome_ref[0]["job_id"] == "uuid-xyz"

    def test_shutdown_after_enqueue_returns_interrupted(self):
        """submit_async_callable on a shut-down dispatcher returns interrupted."""
        self.dispatcher.shutdown()
        result = self.dispatcher.submit_async_callable("req-5", lambda: None, job_id="jid-5")
        assert result["status"] == "interrupted"
        assert result["success"] is False

    def test_async_any_affinity_runs_in_background(self):
        """affinity='any' runs the task in a background thread."""
        done = threading.Event()
        thread_ids = []
        caller_tid = threading.get_ident()

        def task():
            thread_ids.append(threading.get_ident())
            return "bg"

        def on_complete(outcome):
            done.set()

        self.dispatcher.submit_async_callable(
            "req-6", task, affinity="any", on_complete=on_complete
        )
        assert done.wait(timeout=2.0), "background task never completed"
        assert thread_ids[0] != caller_tid, "task ran on caller thread, not background"

    def test_return_envelope_has_expected_keys(self):
        """Pending envelope contains all documented keys."""
        result = self.dispatcher.submit_async_callable("req-7", lambda: None)
        expected_keys = {"request_id", "job_id", "status", "success", "error"}
        assert expected_keys <= set(result.keys())
        self._drain()


# ── MayaStandaloneDispatcher async tests ─────────────────────────────────────


class TestStandaloneSubmitAsync:
    """MayaStandaloneDispatcher.submit_async_callable executes synchronously."""

    def setup_method(self):
        self.dispatcher = MayaStandaloneDispatcher()

    def test_executes_synchronously(self):
        """Standalone dispatcher runs the task before returning."""
        executed = []

        def task():
            executed.append(True)
            return "ok"

        result = self.dispatcher.submit_async_callable("req-s1", task, job_id="sjid-1")
        assert executed, "task was not executed"
        assert result["status"] == "completed"
        assert result["job_id"] == "sjid-1"

    def test_on_complete_called_before_return(self):
        """on_complete is invoked before submit_async_callable returns."""
        call_order = []

        def task():
            call_order.append("task")
            return 99

        def on_complete(outcome):
            call_order.append("callback")

        self.dispatcher.submit_async_callable("req-s2", task, on_complete=on_complete)
        assert call_order == ["task", "callback"]

    def test_failed_task_has_failed_status(self):
        """A task that raises produces status='failed'."""

        def bad_task():
            raise ValueError("oops")

        result = self.dispatcher.submit_async_callable("req-s3", bad_task)
        assert result["status"] == "failed"
        assert result["success"] is False
        assert "oops" in result["error"]
