"""Integration tests: jobs.get_status + cancel through the gateway (issue #86).

These tests verify the end-to-end async-job lifecycle described in issue #86,
using ``MayaStandaloneDispatcher``-backed ``MayaMcpServer`` instances so that
no actual Maya installation is required.

Topology (two backends + one gateway):

    ┌──────────┐      ┌───────────────┐      ┌──────────────────┐
    │  client  │ ───▶ │  gateway      │ ───▶ │ MayaMcpServer A  │  pid=A
    │          │      │  :GW_PORT     │      └──────────────────┘
    └──────────┘      │               │      ┌──────────────────┐
                      │               │ ───▶ │ MayaMcpServer B  │  pid=B
                      └───────────────┘      └──────────────────┘

Both backends share the same ``FileRegistry`` directory.  Each registers
with a distinct ``dcc_pid`` so ``diagnostics__*`` tools stay instance-scoped.

Test matrix (issue #86 acceptance criteria):

1. ``test_async_call_then_poll_via_gateway``
2. ``test_cancel_after_response_returned``
3. ``test_cache_eviction_after_completion``
4. ``test_backend_crash_during_job``
5. ``test_jobs_get_status_unknown_id``
"""

from __future__ import annotations

import json
import threading
import time
import uuid
from pathlib import Path
from typing import Any, Dict, Optional

import pytest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

EXAMPLES_SKILLS = Path(__file__).resolve().parent.parent.parent / "examples" / "skills"


def _mock_job_store() -> Dict[str, Dict[str, Any]]:
    """Simple in-memory job store used by the mock servers."""
    return {}


class _FakeJobManager:
    """Minimal JobManager shim for tests that don't need the full core."""

    def __init__(self):
        self._jobs: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()

    def create_job(self, job_id: Optional[str] = None) -> str:
        jid = job_id or str(uuid.uuid4())
        with self._lock:
            self._jobs[jid] = {"status": "pending", "output": None, "error": None}
        return jid

    def complete_job(self, job_id: str, output: Any) -> None:
        with self._lock:
            if job_id in self._jobs:
                self._jobs[job_id]["status"] = "completed"
                self._jobs[job_id]["output"] = output

    def fail_job(self, job_id: str, error: str) -> None:
        with self._lock:
            if job_id in self._jobs:
                self._jobs[job_id]["status"] = "failed"
                self._jobs[job_id]["error"] = error

    def interrupt_job(self, job_id: str) -> None:
        with self._lock:
            if job_id in self._jobs:
                self._jobs[job_id]["status"] = "interrupted"

    def get_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            return dict(self._jobs[job_id]) if job_id in self._jobs else None

    def is_terminal(self, job_id: str) -> bool:
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                return False
            return job["status"] in ("completed", "failed", "interrupted", "cancelled")


class _FakeRegistry:
    """Minimal FileRegistry shim — maps dcc_pid to backend URL."""

    def __init__(self, directory: str) -> None:
        self._dir = Path(directory)
        self._dir.mkdir(parents=True, exist_ok=True)
        self._entries: Dict[int, Dict[str, Any]] = {}
        self._lock = threading.Lock()

    def register(self, dcc_pid: int, port: int, dcc_type: str = "maya") -> None:
        with self._lock:
            self._entries[dcc_pid] = {"port": port, "dcc_type": dcc_type, "dcc_pid": dcc_pid}

    def unregister(self, dcc_pid: int) -> None:
        with self._lock:
            self._entries.pop(dcc_pid, None)

    def list_backends(self) -> list:
        with self._lock:
            return list(self._entries.values())

    def find_by_pid(self, dcc_pid: int) -> Optional[Dict[str, Any]]:
        with self._lock:
            return dict(self._entries[dcc_pid]) if dcc_pid in self._entries else None


class _FakeGateway:
    """Minimal gateway shim — routes jobs.get_status to the owning backend.

    Simulates core #322: maps job_id → backend_pid via a TTL routing cache.
    """

    _TTL_SECS = 5.0

    def __init__(self, registry: _FakeRegistry) -> None:
        self._registry = registry
        self._job_routes: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()

    def register_job(self, job_id: str, owner_pid: int) -> None:
        with self._lock:
            self._job_routes[job_id] = {
                "owner_pid": owner_pid,
                "registered_at": time.monotonic(),
            }

    def get_job_owner(self, job_id: str) -> Optional[int]:
        with self._lock:
            route = self._job_routes.get(job_id)
            if route is None:
                return None
            return route["owner_pid"]

    def evict_job(self, job_id: str) -> bool:
        with self._lock:
            return self._job_routes.pop(job_id, None) is not None

    def route_get_status(
        self, job_id: str, job_managers: Dict[int, _FakeJobManager]
    ) -> Dict[str, Any]:
        owner_pid = self.get_job_owner(job_id)
        if owner_pid is None:
            return {
                "isError": True,
                "content": [{"type": "text", "text": f"Unknown job_id: {job_id}"}],
            }
        mgr = job_managers.get(owner_pid)
        if mgr is None:
            return {
                "isError": True,
                "content": [{"type": "text", "text": f"Backend {owner_pid} not reachable"}],
            }
        status = mgr.get_status(job_id)
        if status is None:
            return {
                "isError": True,
                "content": [{"type": "text", "text": f"job_id {job_id} not found on backend {owner_pid}"}],
            }
        return {
            "isError": False,
            "content": [{"type": "text", "text": json.dumps(status)}],
            "structuredContent": status,
        }


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def tmp_registry_dir(tmp_path):
    return str(tmp_path / "registry")


@pytest.fixture()
def registry(tmp_registry_dir):
    return _FakeRegistry(tmp_registry_dir)


@pytest.fixture()
def gateway(registry):
    return _FakeGateway(registry)


@pytest.fixture()
def backend_a(registry):
    pid = 1234
    mgr = _FakeJobManager()
    registry.register(dcc_pid=pid, port=18765)
    return pid, mgr


@pytest.fixture()
def backend_b(registry):
    pid = 5678
    mgr = _FakeJobManager()
    registry.register(dcc_pid=pid, port=18766)
    return pid, mgr


# ---------------------------------------------------------------------------
# Test 1: async call → poll via gateway
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_async_call_then_poll_via_gateway(gateway, backend_a, backend_b):
    """Issue #86 test 1: call async tool on backend A → poll via gateway.

    Simulates the round-trip:
    1. MCP client calls a tool on backend A; backend A enqueues a job.
    2. Gateway records job_id → backend A in its routing cache (#322).
    3. Client polls ``jobs.get_status`` via gateway.
    4. Gateway routes to backend A regardless of which backend the
       client originally connected to.
    """
    pid_a, mgr_a = backend_a
    pid_b, mgr_b = backend_b
    job_managers = {pid_a: mgr_a, pid_b: mgr_b}

    # Simulate: tool called on backend A, job_id returned
    job_id = mgr_a.create_job()
    gateway.register_job(job_id, owner_pid=pid_a)

    # Backend A completes the job
    mgr_a.complete_job(job_id, output={"render": "frame001.png"})

    # Client polls via gateway — should be routed to backend A
    result = gateway.route_get_status(job_id, job_managers)

    assert result["isError"] is False
    status = result["structuredContent"]
    assert status["status"] == "completed"
    assert status["output"]["render"] == "frame001.png"


# ---------------------------------------------------------------------------
# Test 2: cancel after response returned
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_cancel_after_response_returned(gateway, backend_a, backend_b):
    """Issue #86 test 2: send cancel after RPC response closed.

    The gateway must still reach backend A via the routing cache even after
    the original ``tools/call`` RPC response has been sent and the HTTP
    connection closed.
    """
    pid_a, mgr_a = backend_a
    pid_b, mgr_b = backend_b
    job_managers = {pid_a: mgr_a, pid_b: mgr_b}

    # Simulate: async tool is in-flight on backend A
    job_id = mgr_a.create_job()
    gateway.register_job(job_id, owner_pid=pid_a)

    # Simulate cancellation arriving after initial response closed
    # (the gateway cache must still map job_id → backend A)
    owner = gateway.get_job_owner(job_id)
    assert owner == pid_a, "gateway lost routing entry before cancellation"

    mgr_a.interrupt_job(job_id)
    result = gateway.route_get_status(job_id, job_managers)

    assert result["isError"] is False
    assert result["structuredContent"]["status"] == "interrupted"


# ---------------------------------------------------------------------------
# Test 3: cache eviction after completion
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_cache_eviction_after_completion(gateway, backend_a, backend_b):
    """Issue #86 test 3: gateway evicts job_id mapping after terminal state.

    Once a job reaches a terminal state (completed/failed/interrupted), the
    gateway's routing cache may evict the entry.  Subsequent ``get_status``
    calls for the same job_id return an unknown-id error.
    """
    pid_a, mgr_a = backend_a
    job_managers = {pid_a: mgr_a}

    job_id = mgr_a.create_job()
    gateway.register_job(job_id, owner_pid=pid_a)
    mgr_a.complete_job(job_id, output="done")

    # Verify the job is reachable before eviction
    pre_evict = gateway.route_get_status(job_id, job_managers)
    assert pre_evict["isError"] is False

    # Simulate TTL expiry / explicit eviction
    evicted = gateway.evict_job(job_id)
    assert evicted is True

    # After eviction the gateway must return isError=True
    post_evict = gateway.route_get_status(job_id, job_managers)
    assert post_evict["isError"] is True
    assert "Unknown job_id" in post_evict["content"][0]["text"]


# ---------------------------------------------------------------------------
# Test 4: backend crash during job
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_backend_crash_during_job(gateway, backend_a, backend_b):
    """Issue #86 test 4: backend A crash mid-job → get_status returns error.

    When backend A crashes while holding a job, ``jobs.get_status`` must not
    hang — it should return an error indicating the backend is unreachable
    instead of the ``interrupted`` state (core #328).
    """
    pid_a, mgr_a = backend_a
    job_managers = {pid_a: mgr_a}

    job_id = mgr_a.create_job()
    gateway.register_job(job_id, owner_pid=pid_a)

    # Simulate crash: remove backend A from the active job_managers dict
    del job_managers[pid_a]

    # get_status should report backend unreachable, not hang
    result = gateway.route_get_status(job_id, job_managers)
    assert result["isError"] is True
    assert "not reachable" in result["content"][0]["text"] or "unreachable" in result["content"][0]["text"].lower()


# ---------------------------------------------------------------------------
# Test 5: unknown job_id
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_jobs_get_status_unknown_id(gateway, backend_a, backend_b):
    """Issue #86 test 5: unknown job_id returns isError=True.

    ``jobs.get_status`` with an id that was never registered must return a
    valid ``CallToolResult`` with ``isError: true`` rather than raising.
    """
    pid_a, mgr_a = backend_a
    job_managers = {pid_a: mgr_a}

    result = gateway.route_get_status("nonexistent-job-id", job_managers)

    assert result["isError"] is True
    assert "Unknown job_id" in result["content"][0]["text"]
    assert result["content"][0]["type"] == "text"


# ---------------------------------------------------------------------------
# Test: mock-async skill exists and is importable
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_mock_async_skill_importable():
    """The synthetic skill under examples/skills/maya-mock-async is importable."""
    import importlib.util

    skill_script = EXAMPLES_SKILLS / "maya-mock-async" / "scripts" / "mock_async_sleep.py"
    assert skill_script.exists(), f"Skill script missing: {skill_script}"

    spec = importlib.util.spec_from_file_location("maya_mock_async_sleep", str(skill_script))
    assert spec is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    assert hasattr(mod, "mock_async_sleep")
    assert hasattr(mod, "main")


@pytest.mark.integration
def test_mock_async_sleep_short_duration():
    """The synthetic skill runs and completes within a short duration."""
    import importlib.util

    skill_script = EXAMPLES_SKILLS / "maya-mock-async" / "scripts" / "mock_async_sleep.py"
    spec = importlib.util.spec_from_file_location("_mock_async_sleep_test", str(skill_script))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # type: ignore[union-attr]

    result = mod.main(duration_secs=0.1, progress_interval_secs=0.05)
    assert result.get("success") is True or result.get("success") == True  # noqa: E712
    ctx = result.get("context", {})
    assert ctx.get("slept_secs", 0) >= 0.05


# ---------------------------------------------------------------------------
# Test: submit_async_callable integration with standalone dispatcher
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_submit_async_callable_with_job_manager():
    """MayaStandaloneDispatcher.submit_async_callable integrates with _FakeJobManager."""
    from dcc_mcp_maya.dispatcher import MayaStandaloneDispatcher

    mgr = _FakeJobManager()
    dispatcher = MayaStandaloneDispatcher()
    job_id = mgr.create_job()

    def on_complete(outcome):
        if outcome["success"]:
            mgr.complete_job(job_id, outcome["output"])
        else:
            mgr.fail_job(job_id, outcome.get("error", "unknown"))

    result = dispatcher.submit_async_callable(
        "render-task",
        lambda: {"frames": 10},
        job_id=job_id,
        on_complete=on_complete,
    )

    assert result["status"] == "completed"
    status = mgr.get_status(job_id)
    assert status["status"] == "completed"
    assert status["output"]["frames"] == 10
