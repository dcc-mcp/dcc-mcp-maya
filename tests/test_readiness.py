"""Unit tests for the runtime readiness wiring (issue #184).

Covers the three transitions that ``/v1/readyz`` needs to stop lying
during Maya's boot window:

* ``process = True``    — always, once the Python interpreter is up.
* ``dispatcher = True`` — after ``HostExecutionBridge`` wires the
  in-process executor.
* ``dcc = True``        — after Maya's main thread pumps the first
  deferred no-op job (or synchronously on
  :class:`MayaStandaloneDispatcher`).

The Maya adapter **wraps** :class:`dcc_mcp_core.ReadinessProbe` (core
0.14.28+) — these tests exercise only the Maya-side plumbing
(:class:`dcc_mcp_maya.ReadinessBinder`, env-var resolution, dispatcher
scheduling, and the ``set_readiness_probe`` publish hop).  The probe's
own state machine is unit-tested upstream by ``dcc-mcp-core``.

The tests avoid importing a real Maya — they use a fake dispatcher for
the "never pumps" case and :class:`MayaStandaloneDispatcher` for the
"flips synchronously" case, matching the harness style already used by
``tests/test_dispatcher.py``.
"""

from __future__ import annotations

from typing import Any, Callable, List, Optional
from unittest.mock import MagicMock

import pytest
from dcc_mcp_core import ReadinessProbe

from dcc_mcp_maya import (
    ENV_READINESS_TIMEOUT_SECS,
    MayaStandaloneDispatcher,
    ReadinessBinder,
    install_readiness,
    resolve_readiness_timeout_secs,
)

# ---------------------------------------------------------------------------
# resolve_readiness_timeout_secs
# ---------------------------------------------------------------------------


class TestResolveReadinessTimeout:
    """Env-var + explicit-argument resolution."""

    def test_returns_none_when_nothing_configured(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv(ENV_READINESS_TIMEOUT_SECS, raising=False)
        assert resolve_readiness_timeout_secs() is None

    def test_explicit_argument_wins(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv(ENV_READINESS_TIMEOUT_SECS, "30")
        assert resolve_readiness_timeout_secs(5) == 5

    def test_reads_env_var_when_argument_is_none(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv(ENV_READINESS_TIMEOUT_SECS, "12")
        assert resolve_readiness_timeout_secs() == 12

    def test_non_integer_env_collapses_to_none(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv(ENV_READINESS_TIMEOUT_SECS, "twelve")
        assert resolve_readiness_timeout_secs() is None

    def test_non_positive_collapses_to_none(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv(ENV_READINESS_TIMEOUT_SECS, "0")
        assert resolve_readiness_timeout_secs() is None
        monkeypatch.setenv(ENV_READINESS_TIMEOUT_SECS, "-5")
        assert resolve_readiness_timeout_secs() is None

    def test_empty_env_treated_as_unset(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv(ENV_READINESS_TIMEOUT_SECS, "   ")
        assert resolve_readiness_timeout_secs() is None

    def test_invalid_explicit_argument_returns_none(self) -> None:
        # Strings are not valid positive integers here.
        assert resolve_readiness_timeout_secs("oops") is None  # type: ignore[arg-type]
        assert resolve_readiness_timeout_secs(-1) is None


# ---------------------------------------------------------------------------
# Dispatcher probe helpers + fake server
# ---------------------------------------------------------------------------


class _NeverPumpingDispatcher:
    """Fake UI dispatcher that *accepts* jobs but never runs them.

    Mimics a Maya that has its HTTP listener up (process green) and the
    host execution bridge attached (dispatcher green) but whose main thread
    is still booting — the deferred callback never fires, so ``dcc``
    must stay red.
    """

    def __init__(self) -> None:
        self.received: List[Any] = []

    def submit_async_callable(
        self,
        *,
        request_id: str,
        task: Callable[[], Any],
        affinity: str = "main",
        timeout_ms: int = 5_000,
        on_complete: Optional[Callable[[Any], None]] = None,
        **_: Any,
    ) -> dict:
        # Record the call but never invoke the callback.
        self.received.append(
            {
                "request_id": request_id,
                "affinity": affinity,
                "has_callback": on_complete is not None,
            }
        )
        return {"request_id": request_id, "status": "pending"}


class _FakeInnerServer:
    """Stand-in for the Rust ``McpHttpServer`` — records the published probe."""

    def __init__(self) -> None:
        self.published_probe: Any = None

    def set_readiness_probe(self, probe: Any) -> None:
        self.published_probe = probe


class _FakeServer:
    """Minimal ``MayaMcpServer`` stand-in with just the attributes ReadinessBinder touches."""

    def __init__(self, dispatcher: Any = None) -> None:
        self._maya_dispatcher = dispatcher
        self._server = _FakeInnerServer()


def _assert_ready_bits(report: dict, *, process: bool, dispatcher: bool, dcc: bool) -> None:
    """Assert Maya's readiness bits while allowing core to add diagnostics."""
    assert report["process"] is process
    assert report["dispatcher"] is dispatcher
    assert report["dcc"] is dcc


# ---------------------------------------------------------------------------
# ReadinessBinder.bind — the core contract
# ---------------------------------------------------------------------------


class TestReadinessBinderBind:
    """Transitions driven by :meth:`ReadinessBinder.bind`."""

    def test_bind_with_no_dispatcher_flips_all_green_inline_mode(self) -> None:
        """Inline executor mode (no host dispatcher) collapses the probe to green.

        When no host dispatcher is attached, every ``tools/call`` runs
        on the HTTP worker thread — there is no
        separate Maya main thread to wait on, so the three-state probe
        reduces to "handler routing is live", which is already true the
        moment :meth:`bind` is called.
        """
        server = _FakeServer(dispatcher=None)
        binder = ReadinessBinder()
        bound = binder.bind(server)
        assert bound is True
        _assert_ready_bits(binder.report(), process=True, dispatcher=True, dcc=True)

    def test_bind_with_standalone_flips_both_bits_synchronously(self) -> None:
        """:class:`MayaStandaloneDispatcher` runs callbacks on the calling thread."""
        server = _FakeServer(dispatcher=MayaStandaloneDispatcher())
        binder = ReadinessBinder()
        bound = binder.bind(server)
        assert bound is True
        assert binder.is_ready() is True
        _assert_ready_bits(binder.report(), process=True, dispatcher=True, dcc=True)

    def test_bind_with_never_pumping_dispatcher_keeps_dcc_red(self) -> None:
        dispatcher = _NeverPumpingDispatcher()
        server = _FakeServer(dispatcher=dispatcher)
        binder = ReadinessBinder()
        bound = binder.bind(server)
        # We *did* accept the probe (returned True from default scheduler)
        # and flipped dispatcher=True, but the callback never fires so
        # dcc stays red.
        assert bound is True
        snap = binder.report()
        assert snap["dispatcher"] is True
        assert snap["dcc"] is False
        # The scheduler used the main-thread affinity as expected.
        assert dispatcher.received, "dispatcher should have recorded one submit"
        call = dispatcher.received[0]
        assert call["affinity"] == "main"
        assert call["has_callback"] is True

    def test_bind_with_post_tick_dispatcher_flips_dcc_optimistically(self) -> None:
        """Core's ``BlockingDispatcher`` / ``QueueDispatcher`` use a post/tick
        protocol — no ``submit_async_callable``, no per-job callback.  The
        binder must recognise that shape and flip ``dcc`` immediately so
        real-world plugin-driven servers don't get stuck at 503.
        """

        class _PostTickDispatcher:
            """Minimal stand-in for core's ``BlockingDispatcher`` shape."""

            def post(self, _callback: Any) -> None:
                pass

            def tick(self) -> None:
                pass

        server = _FakeServer(dispatcher=_PostTickDispatcher())
        binder = ReadinessBinder()
        bound = binder.bind(server)
        assert bound is True
        _assert_ready_bits(binder.report(), process=True, dispatcher=True, dcc=True)

    def test_bind_is_idempotent(self) -> None:
        server = _FakeServer(dispatcher=MayaStandaloneDispatcher())
        binder = ReadinessBinder()
        assert binder.bind(server) is True
        # Second bind on the same server is a no-op and returns the
        # previously-recorded scheduling state.
        assert binder.bind(server) is True
        assert binder.is_ready() is True

    def test_custom_probe_scheduler_is_used(self) -> None:
        """Injected scheduler overrides the default :func:`submit_async_callable` path."""
        flipped: List[bool] = []

        def scheduler(_dispatcher: Any, on_done: Callable[[], None]) -> bool:
            on_done()
            flipped.append(True)
            return True

        binder = ReadinessBinder(probe_scheduler=scheduler)
        server = _FakeServer(dispatcher=MagicMock(name="unused-dispatcher"))
        assert binder.bind(server) is True
        assert flipped == [True]
        assert binder.is_ready() is True

    def test_bind_publishes_probe_to_inner_server(self) -> None:
        """``set_readiness_probe`` is called with the same probe the binder wraps."""
        server = _FakeServer(dispatcher=MayaStandaloneDispatcher())
        binder = ReadinessBinder()
        assert binder.bind(server) is True
        # The inner Rust server recorded the exact probe instance.
        assert server._server.published_probe is binder.probe
        assert binder.published_to_server is True

    def test_mark_dispatcher_ready_is_idempotent(self) -> None:
        binder = ReadinessBinder()
        binder.mark_dispatcher_ready()
        binder.mark_dispatcher_ready()
        assert binder.report()["dispatcher"] is True
        binder.mark_dispatcher_ready(False)
        assert binder.report()["dispatcher"] is False

    def test_mark_dcc_ready_flips_dcc_bit(self) -> None:
        binder = ReadinessBinder()
        binder.mark_dcc_ready(True)
        assert binder.report()["dcc"] is True


# ---------------------------------------------------------------------------
# install_readiness — module-level convenience
# ---------------------------------------------------------------------------


class TestInstallReadiness:
    def test_returns_binder_ready_on_inline_mode(self) -> None:
        """Inline mode (no host dispatcher) — ``install_readiness`` lands green."""
        server = _FakeServer(dispatcher=None)
        binder = install_readiness(server)
        assert isinstance(binder, ReadinessBinder)
        snap = binder.report()
        assert snap["dispatcher"] is True
        assert snap["dcc"] is True

    def test_threads_timeout_through(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv(ENV_READINESS_TIMEOUT_SECS, raising=False)
        server = _FakeServer(dispatcher=MayaStandaloneDispatcher())
        binder = install_readiness(server, timeout_secs=45)
        assert binder.timeout_secs == 45


# ---------------------------------------------------------------------------
# Integration with MayaMcpServer
# ---------------------------------------------------------------------------


class TestMayaMcpServerReadinessIntegration:
    """End-to-end: constructor + ``attach_dispatcher`` drive the probe."""

    def test_construction_without_dispatcher_is_green_inline_mode(self) -> None:
        """Inline executor mode (the ``start_server(host_dispatcher=None)``
        path used by many tests and ``mayapy`` batch scripts) is
        instantly ready — every call runs on the HTTP worker thread so
        there's no separate main thread to wait on.
        """
        from dcc_mcp_maya import MayaMcpServer

        server = MayaMcpServer(port=0)
        try:
            _assert_ready_bits(
                server.readiness_report(),
                process=True,
                dispatcher=True,
                dcc=True,
            )
            assert server.readiness is not None
            # The binder published its probe to the inner Rust server
            # via ``set_readiness_probe`` (core 0.14.28+).
            assert server.readiness.published_to_server is True
        finally:
            try:
                server.stop()
            except Exception:  # noqa: BLE001
                pass

    def test_attach_dispatcher_keeps_probe_green(self) -> None:
        """Attaching a dispatcher after construction is idempotent.

        The server starts in inline mode (all green).  Attaching a real
        host dispatcher later still leaves the probe green — the binder
        re-runs, but since :class:`MayaStandaloneDispatcher` pumps the
        probe job synchronously it lands at the same all-green state.
        """
        from dcc_mcp_maya import MayaMcpServer

        server = MayaMcpServer(port=0)
        try:
            assert server.readiness_report()["dcc"] is True  # inline mode
            server.attach_dispatcher(MayaStandaloneDispatcher())
            snap = server.readiness_report()
            assert snap["dispatcher"] is True
            assert snap["dcc"] is True
        finally:
            try:
                server.stop()
            except Exception:  # noqa: BLE001
                pass

    def test_constructor_with_dispatcher_lands_all_green(self) -> None:
        from dcc_mcp_maya import MayaMcpServer

        server = MayaMcpServer(
            port=0,
            host_dispatcher=MayaStandaloneDispatcher(),
        )
        try:
            _assert_ready_bits(
                server.readiness_report(),
                process=True,
                dispatcher=True,
                dcc=True,
            )
        finally:
            try:
                server.stop()
            except Exception:  # noqa: BLE001
                pass

    def test_readiness_probe_handle_is_core_instance(self) -> None:
        """``server.readiness.probe`` is a real :class:`dcc_mcp_core.ReadinessProbe`."""
        from dcc_mcp_maya import MayaMcpServer

        server = MayaMcpServer(port=0)
        try:
            assert isinstance(server.readiness.probe, ReadinessProbe)
        finally:
            try:
                server.stop()
            except Exception:  # noqa: BLE001
                pass

    def test_readiness_timeout_is_resolved_from_kwarg(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from dcc_mcp_maya import MayaMcpServer

        monkeypatch.delenv(ENV_READINESS_TIMEOUT_SECS, raising=False)
        server = MayaMcpServer(port=0, readiness_timeout_secs=42)
        try:
            assert server.readiness.timeout_secs == 42
        finally:
            try:
                server.stop()
            except Exception:  # noqa: BLE001
                pass

    def test_readiness_timeout_is_resolved_from_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from dcc_mcp_maya import MayaMcpServer

        monkeypatch.setenv(ENV_READINESS_TIMEOUT_SECS, "17")
        server = MayaMcpServer(port=0)
        try:
            assert server.readiness.timeout_secs == 17
        finally:
            try:
                server.stop()
            except Exception:  # noqa: BLE001
                pass
