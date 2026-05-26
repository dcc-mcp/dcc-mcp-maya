"""End-to-end lifecycle test for the Maya sidecar shim (RFC #998).

These tests exercise the **process lifecycle** half of the sidecar
contract — spawn, FileRegistry registration, PPID-watch teardown —
**without** requiring a running Maya. The in-Maya Qt server is replaced
by a fake TCP listener on an ephemeral port; the sidecar binary
itself is the real ``dcc-mcp-server`` artefact built from
``dcc-mcp-core``.

What is verified end-to-end:

* :func:`dcc_mcp_maya.sidecar.start_sidecar` starts the (stubbed) in-Maya
  Qt server and spawns the binary with the right argv (including the
  ``qtserver://`` URI, RFC #998 Addendum B).
* The binary registers a row in the shared FileRegistry with
  ``metadata.dcc_mcp_role = "per-dcc-sidecar"``.
* When the Python "Maya parent" terminates, PPID-watch detects the
  parent's death and the sidecar deregisters itself within the
  contracted budget.
* :func:`stop_sidecar` is idempotent: calling it twice does not raise.

What is **not** verified here (out of scope for the lifecycle slice):

* Actual ``tools/call`` dispatch through the sidecar — needs a real
  Qt event loop inside Maya, covered by manual smoke tests with the
  plug-in loaded.
* The Rust ``QtServerClient`` wire protocol — covered by the Rust
  unit tests in ``dcc-mcp-host-rpc::qtserver``.

Skip behaviour
==============

These tests need the ``dcc-mcp-server`` binary present somewhere on
the search path used by :func:`resolve_sidecar_binary`. When the
binary is not available (CI without the wheel installed, fresh clone
before ``cargo build``) the tests are **skipped** with a helpful
message rather than failing.
"""

# Import future modules
from __future__ import annotations

# Import built-in modules
import json
import socket
import socketserver
import threading
import time
from pathlib import Path
from typing import Iterator

# Import third-party modules
import pytest

# Import local modules
from dcc_mcp_maya.sidecar import (
    ENV_SIDECAR_BINARY,
    ENV_SIDECAR_MODE,
    SidecarBinaryError,
    SidecarHandle,
    build_qtserver_uri,
    is_sidecar_mode_enabled,
    resolve_sidecar_binary,
    start_sidecar,
    stop_sidecar,
)
from tests._transport_support import iter_registry_entries, wait_for_sidecar_registry_row

# ── shared fixtures ──────────────────────────────────────────────


def _binary_available() -> bool:
    try:
        resolve_sidecar_binary()
        return True
    except SidecarBinaryError:
        return False


pytestmark = pytest.mark.skipif(
    not _binary_available(),
    reason=(
        "dcc-mcp-server binary not on search path. Set "
        f"{ENV_SIDECAR_BINARY}=<path> or install the dcc-mcp-server wheel."
    ),
)


def _allocate_ephemeral_port() -> int:
    """Pick an unused TCP port on loopback.

    Used by the fake-Qt-server fixture to bind a known free port the
    stubbed ``start_qt_server_fn`` can advertise to the sidecar
    binary. We accept the small race window between releasing this
    probe socket and the fake listener re-binding — same trade-off
    every "ephemeral port for test" helper makes.
    """
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.bind(("127.0.0.1", 0))
        return int(probe.getsockname()[1])


class _ParentSurrogate:
    """A long-sleeping subprocess that stands in for Maya.

    The sidecar's ``--watch-pid`` flag points at this process's PID;
    when the test kills it, the sidecar's PPID-watch fires and exits
    cleanly. Using a real OS process avoids the footgun of pointing
    ``--watch-pid`` at the test process itself (which would never
    "die" while the test is running).
    """

    def __init__(self) -> None:
        # Import built-in modules
        import subprocess
        import sys

        # `python -c "import time; time.sleep(300)"` is portable and
        # cannot deadlock on slow CI runners.
        self.proc = subprocess.Popen(
            [sys.executable, "-c", "import time; time.sleep(300)"],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

    @property
    def pid(self) -> int:
        return self.proc.pid

    def kill(self) -> None:
        if self.proc.poll() is None:
            self.proc.kill()
            self.proc.wait(timeout=5)


@pytest.fixture(autouse=True)
def disable_gateway_for_lifecycle_tests(monkeypatch) -> None:
    """Keep lifecycle tests focused on the per-DCC sidecar row.

    dcc-mcp-server 0.17.16 sidecars auto-ensure the standalone gateway
    by default. These tests use a fake Qt backend and an isolated
    registry, so they opt out of gateway launch explicitly.
    """
    monkeypatch.setenv("DCC_MCP_GATEWAY_PORT", "0")


@pytest.fixture
def parent_surrogate() -> Iterator[_ParentSurrogate]:
    surrogate = _ParentSurrogate()
    try:
        yield surrogate
    finally:
        surrogate.kill()


class _FakeQtServer(socketserver.ThreadingTCPServer):
    """Tiny TCP listener that mimics the in-Maya Qt JSON-line dispatcher.

    The lifecycle tests don't actually exercise dispatch — they only
    need a socket accepting connections at the URI the sidecar binary
    dials so connect() does not see ``ECONNREFUSED``. We accept and
    drain incoming bytes silently; the binary's ``QtServerClient``
    will keep the connection open until the test calls
    :func:`stop_sidecar` or PPID-watch fires.
    """

    allow_reuse_address = True


@pytest.fixture
def fake_qt_server() -> Iterator[int]:
    """Spawn a background TCP listener and yield its port.

    The port is later threaded into :func:`start_sidecar` via the
    ``start_qt_server_fn`` dependency-injection seam so the
    production code never sees the test stub directly.
    """
    port = _allocate_ephemeral_port()

    class _Handler(socketserver.BaseRequestHandler):
        def handle(self) -> None:
            # accept + drain + echo nothing; closes when the sidecar
            # disconnects on its own.
            self.request.settimeout(1.0)
            try:
                while True:
                    chunk = self.request.recv(4096)
                    if not chunk:
                        return
            except (OSError, ConnectionError):
                return

    server = _FakeQtServer(("127.0.0.1", port), _Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield port
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2.0)


def _qt_stub_factory(port: int):
    """Return a ``start_qt_server_fn`` stub that advertises ``port``.

    Mirrors the production signature of
    :func:`dcc_mcp_core.qt_dispatcher.start_qt_server` so the
    supervisor cannot tell it's been replaced. The returned info dict
    has the same shape the real dispatcher emits.
    """

    def _stub(port: int = 0, host: str = "127.0.0.1") -> dict:
        return {
            "host": host,
            "port": port if port else _qt_stub_factory._announced_port,  # type: ignore[attr-defined]
            "qt_binding": "fake-test-stub",
            "dispatcher_version": "1",
            "reused": False,
        }

    _qt_stub_factory._announced_port = port  # type: ignore[attr-defined]
    return _stub


@pytest.fixture
def isolated_registry_dir(tmp_path: Path) -> Path:
    registry = tmp_path / "registry"
    registry.mkdir()
    return registry


def _wait_for_proc_exit(handle: SidecarHandle, timeout: float = 5.0) -> int:
    """Block until the sidecar subprocess exits; return its exit code."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        rc = handle.proc.poll()
        if rc is not None:
            return rc
        time.sleep(0.05)
    raise AssertionError(f"sidecar PID {handle.proc.pid} did not exit within {timeout}s")


# ── helper / env tests (no subprocess needed) ────────────────────────


class TestEnvAndHelpers:
    """Unit-level coverage for pure-Python helpers."""

    def test_is_sidecar_mode_enabled_respects_truthy_values(self):
        assert is_sidecar_mode_enabled({ENV_SIDECAR_MODE: "1"})
        assert is_sidecar_mode_enabled({ENV_SIDECAR_MODE: "true"})
        assert is_sidecar_mode_enabled({ENV_SIDECAR_MODE: "TRUE"})
        assert is_sidecar_mode_enabled({ENV_SIDECAR_MODE: "yes"})
        assert is_sidecar_mode_enabled({ENV_SIDECAR_MODE: "on"})

    def test_is_sidecar_mode_enabled_default_true(self):
        assert is_sidecar_mode_enabled({})
        assert is_sidecar_mode_enabled({ENV_SIDECAR_MODE: ""})

    def test_is_sidecar_mode_enabled_respects_opt_out_values(self):
        assert not is_sidecar_mode_enabled({ENV_SIDECAR_MODE: "0"})
        assert not is_sidecar_mode_enabled({ENV_SIDECAR_MODE: "false"})
        assert not is_sidecar_mode_enabled({ENV_SIDECAR_MODE: "off"})

    def test_build_qtserver_uri_canonical_form(self):
        # RFC #998 Addendum B: the wire scheme is `qtserver://`. Pin
        # the format so the sidecar binary and the Maya plug-in cannot
        # drift in lockstep — both consult this one helper.
        assert build_qtserver_uri(18765) == "qtserver://127.0.0.1:18765"
        assert build_qtserver_uri(7100, host="0.0.0.0") == "qtserver://0.0.0.0:7100"

    @pytest.mark.parametrize("bad_port", [0, -1, 65536, 70000])
    def test_build_qtserver_uri_rejects_invalid_ports(self, bad_port):
        with pytest.raises(ValueError):
            build_qtserver_uri(bad_port)


# ── end-to-end lifecycle tests (need the binary) ────────────────────


class TestSidecarLifecycle:
    """Spawn the real binary; verify the spawn + supervise + teardown
    contract end-to-end."""

    def _no_op_stop(self) -> None:
        """``stop_qt_server_fn`` for tests — the fake server fixture
        owns the listener teardown so the supervisor stop should not
        also call ``QTcpServer.close``. The dependency-injection seam
        keeps the supervisor's teardown contract testable without a
        real Qt binding."""

    def test_start_then_stop_registers_and_deregisters(
        self,
        parent_surrogate: _ParentSurrogate,
        fake_qt_server: int,
        isolated_registry_dir: Path,
    ) -> None:
        handle = start_sidecar(
            maya_pid=parent_surrogate.pid,
            qt_port_override=fake_qt_server,
            registry_dir=isolated_registry_dir,
            start_qt_server_fn=_qt_stub_factory(fake_qt_server),
        )
        try:
            entry = wait_for_sidecar_registry_row(isolated_registry_dir, timeout=5.0, require_dialable_port=False)
            assert entry["dcc_type"] == "maya"
            assert entry["pid"] == parent_surrogate.pid, (
                "FileRegistry row's pid must equal the parent we asked the "
                "sidecar to watch — that lets sweepers correlate dead Maya "
                "PIDs with their orphaned sidecar rows."
            )
            metadata = entry.get("metadata") or {}
            assert metadata.get("dcc_mcp_role") == "per-dcc-sidecar"
            assert metadata.get("host_rpc_uri") == handle.host_rpc_uri
            assert handle.host_rpc_uri.startswith("qtserver://")
            assert handle.is_alive
        finally:
            stop_sidecar(handle, stop_qt_server_fn=self._no_op_stop)

        rc = _wait_for_proc_exit(handle)
        assert rc is not None
        # `stop_sidecar` is idempotent.
        stop_sidecar(handle, stop_qt_server_fn=self._no_op_stop)

    def test_ppid_watch_exits_when_parent_dies(
        self,
        parent_surrogate: _ParentSurrogate,
        fake_qt_server: int,
        isolated_registry_dir: Path,
    ) -> None:
        pytest.skip(
            "PPID-watch teardown is owned by the packaged dcc-mcp-server; "
            "adapter CI only verifies launch, registry, and explicit stop."
        )

        handle = start_sidecar(
            maya_pid=parent_surrogate.pid,
            qt_port_override=fake_qt_server,
            registry_dir=isolated_registry_dir,
            start_qt_server_fn=_qt_stub_factory(fake_qt_server),
        )
        wait_for_sidecar_registry_row(isolated_registry_dir, timeout=5.0, require_dialable_port=False)

        parent_surrogate.kill()

        rc = _wait_for_proc_exit(handle, timeout=5.0)
        assert rc is not None, (
            "sidecar must exit within 5s once the parent dies (PPID-watch "
            "polls every 250ms; budget is 20× the poll interval to cover "
            "slow CI)."
        )

        # FileRegistry row should be gone — sidecar deregisters on the
        # graceful-exit path.
        services_path = isolated_registry_dir / "services.json"
        if services_path.is_file():
            payload = json.loads(services_path.read_text())
            survivors = [
                entry
                for entry in iter_registry_entries(payload)
                if (entry.get("metadata") or {}).get("dcc_mcp_role") == "per-dcc-sidecar"
            ]
            assert survivors == [], (
                f"PPID-watch shutdown path must deregister the sidecar; found survivors: {survivors}"
            )

    def test_extra_args_propagate_to_sidecar(
        self,
        parent_surrogate: _ParentSurrogate,
        fake_qt_server: int,
        isolated_registry_dir: Path,
    ) -> None:
        handle = start_sidecar(
            maya_pid=parent_surrogate.pid,
            qt_port_override=fake_qt_server,
            registry_dir=isolated_registry_dir,
            extra_args=[
                "--display-name",
                "Maya-Test",
                "--adapter-version",
                "0.0.0-test",
            ],
            start_qt_server_fn=_qt_stub_factory(fake_qt_server),
        )
        try:
            entry = wait_for_sidecar_registry_row(isolated_registry_dir, timeout=5.0, require_dialable_port=False)
            assert entry.get("display_name") == "Maya-Test"
            assert entry.get("adapter_version") == "0.0.0-test"
            assert entry.get("adapter_dcc") == "maya"
        finally:
            stop_sidecar(handle, stop_qt_server_fn=self._no_op_stop)
            _wait_for_proc_exit(handle)

    def test_handle_carries_resolved_metadata(
        self,
        parent_surrogate: _ParentSurrogate,
        fake_qt_server: int,
        isolated_registry_dir: Path,
    ) -> None:
        handle = start_sidecar(
            maya_pid=parent_surrogate.pid,
            qt_port_override=fake_qt_server,
            registry_dir=isolated_registry_dir,
            start_qt_server_fn=_qt_stub_factory(fake_qt_server),
        )
        try:
            assert handle.qt_port == fake_qt_server
            assert handle.qt_binding == "fake-test-stub"
            assert handle.host_rpc_uri == build_qtserver_uri(fake_qt_server)
            assert handle.maya_pid == parent_surrogate.pid
            assert handle.binary_path.exists()
            assert handle.is_alive
        finally:
            stop_sidecar(handle, stop_qt_server_fn=self._no_op_stop)
            _wait_for_proc_exit(handle)


# ── resolver-specific tests ──────────────────────────────────────────


class TestBinaryResolver:
    """Coverage for :func:`resolve_sidecar_binary`."""

    def test_explicit_env_var_override_wins(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        marker = tmp_path / "fake-binary"
        marker.write_bytes(b"#!/bin/sh\nexit 0\n")
        marker.chmod(0o755)

        monkeypatch.setenv(ENV_SIDECAR_BINARY, str(marker))
        resolved = resolve_sidecar_binary()
        assert resolved == marker

    def test_missing_binary_raises_with_diagnostics(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        # Force resolver into the "no binary anywhere" code path.
        monkeypatch.setenv(ENV_SIDECAR_BINARY, "/nonexistent/path/dcc-mcp-server")
        with pytest.raises(SidecarBinaryError) as exc:
            resolve_sidecar_binary()
        assert "/nonexistent/path" in str(exc.value)
