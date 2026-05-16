"""End-to-end lifecycle test for the Maya sidecar shim (RFC #998).

These tests exercise the **process lifecycle** half of the sidecar
contract — spawn, FileRegistry registration, PPID-watch teardown —
**without** requiring a running Maya. The Maya commandPort is replaced
by a fake TCP listener on a free port; the sidecar binary itself is
the real ``dcc-mcp-server`` artefact built from ``dcc-mcp-core``.

What is verified end-to-end:

* :func:`dcc_mcp_maya.sidecar.start_sidecar` spawns the binary with
  the right argv.
* The binary registers a row in the shared FileRegistry with
  ``metadata.dcc_mcp_role = "per-dcc-sidecar"``.
* When the Python "Maya parent" terminates, PPID-watch detects the
  parent's death and the sidecar deregisters itself within the
  contracted budget.
* :func:`stop_sidecar` is idempotent: calling it twice does not raise.

What is **not** verified here (out of scope for the lifecycle slice):

* Actual ``tools/call`` dispatch through the sidecar — needs the
  URI-router-with-HostRpcClient wiring on the sidecar binary side,
  which is the next core PR.
* Real Maya commandPort behaviour — tested manually with the loaded
  plug-in inside Maya. The pytest fake-commandPort listener is
  enough to confirm the spawn argv is correct.

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
import os
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
    allocate_free_port,
    build_host_rpc_uri,
    is_sidecar_mode_enabled,
    resolve_sidecar_binary,
    start_sidecar,
    stop_sidecar,
)

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


@pytest.fixture
def parent_surrogate() -> Iterator[_ParentSurrogate]:
    surrogate = _ParentSurrogate()
    try:
        yield surrogate
    finally:
        surrogate.kill()


class _FakeCommandPort(socketserver.ThreadingTCPServer):
    """Tiny TCP listener that mimics Maya's commandPort acceptor.

    Tests don't actually need the wire format — the sidecar's MVP
    doesn't dispatch yet (the URI router lands in a follow-up). We
    just need a listening socket on the port advertised in
    ``--host-rpc`` so a future smoke test that DOES dial in won't
    get ``ECONNREFUSED``.
    """

    allow_reuse_address = True


@pytest.fixture
def fake_command_port() -> Iterator[int]:
    port = allocate_free_port()

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

    server = _FakeCommandPort(("127.0.0.1", port), _Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield port
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2.0)


@pytest.fixture
def isolated_registry_dir(tmp_path: Path) -> Path:
    registry = tmp_path / "registry"
    registry.mkdir()
    return registry


def _wait_for_registry_row(registry_dir: Path, timeout: float = 5.0) -> dict:
    """Poll ``services.json`` until a per-dcc-sidecar row appears."""
    services_path = registry_dir / "services.json"
    deadline = time.monotonic() + timeout
    last_err: Exception | None = None
    while time.monotonic() < deadline:
        if services_path.is_file():
            try:
                payload = json.loads(services_path.read_text())
            except json.JSONDecodeError as exc:
                last_err = exc
            else:
                for entry in _iter_entries(payload):
                    metadata = entry.get("metadata") or {}
                    if metadata.get("dcc_mcp_role") == "per-dcc-sidecar":
                        return entry
        time.sleep(0.05)
    raise AssertionError(
        f"per-dcc-sidecar row never appeared in {services_path} within "
        f"{timeout}s. Last JSON error: {last_err}. "
        f"Final contents: {services_path.read_text() if services_path.is_file() else '<missing>'}"
    )


def _iter_entries(payload: object) -> Iterator[dict]:
    """Yield service entries regardless of which container shape the
    Rust ``FileRegistry`` flushed (``services.json`` schema has changed
    a few times — be liberal in what we accept)."""
    if isinstance(payload, list):
        for item in payload:
            if isinstance(item, dict):
                yield item
    elif isinstance(payload, dict):
        services = payload.get("services")
        if isinstance(services, list):
            for item in services:
                if isinstance(item, dict):
                    yield item
        elif isinstance(services, dict):
            for item in services.values():
                if isinstance(item, dict):
                    yield item
        else:
            # Top-level mapping of key -> entry
            for value in payload.values():
                if isinstance(value, dict) and "dcc_type" in value:
                    yield value


def _wait_for_proc_exit(handle: SidecarHandle, timeout: float = 5.0) -> int:
    """Block until the sidecar subprocess exits; return its exit code."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        rc = handle.proc.poll()
        if rc is not None:
            return rc
        time.sleep(0.05)
    raise AssertionError(
        f"sidecar PID {handle.proc.pid} did not exit within {timeout}s"
    )


# ── helper / env tests (no subprocess needed) ────────────────────────


class TestEnvAndHelpers:
    """Unit-level coverage for pure-Python helpers."""

    def test_is_sidecar_mode_enabled_respects_truthy_values(self):
        assert is_sidecar_mode_enabled({ENV_SIDECAR_MODE: "1"})
        assert is_sidecar_mode_enabled({ENV_SIDECAR_MODE: "true"})
        assert is_sidecar_mode_enabled({ENV_SIDECAR_MODE: "TRUE"})
        assert is_sidecar_mode_enabled({ENV_SIDECAR_MODE: "yes"})
        assert is_sidecar_mode_enabled({ENV_SIDECAR_MODE: "on"})

    def test_is_sidecar_mode_enabled_default_false(self):
        assert not is_sidecar_mode_enabled({})
        assert not is_sidecar_mode_enabled({ENV_SIDECAR_MODE: ""})
        assert not is_sidecar_mode_enabled({ENV_SIDECAR_MODE: "0"})
        assert not is_sidecar_mode_enabled({ENV_SIDECAR_MODE: "false"})

    def test_allocate_free_port_returns_usable_port(self):
        port = allocate_free_port()
        assert 1 < port < 65536
        # Sanity-check that we can actually bind it.
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
            probe.bind(("127.0.0.1", port))

    def test_build_host_rpc_uri_canonical_form(self):
        assert build_host_rpc_uri(6042) == "commandport://127.0.0.1:6042"
        assert (
            build_host_rpc_uri(7100, host="0.0.0.0")
            == "commandport://0.0.0.0:7100"
        )

    @pytest.mark.parametrize("bad_port", [0, -1, 65536, 70000])
    def test_build_host_rpc_uri_rejects_invalid_ports(self, bad_port):
        with pytest.raises(ValueError):
            build_host_rpc_uri(bad_port)


# ── end-to-end lifecycle tests (need the binary) ────────────────────


class TestSidecarLifecycle:
    """Spawn the real binary; verify the spawn + supervise + teardown
    contract end-to-end."""

    def test_start_then_stop_registers_and_deregisters(
        self,
        parent_surrogate: _ParentSurrogate,
        fake_command_port: int,
        isolated_registry_dir: Path,
    ) -> None:
        handle = start_sidecar(
            maya_pid=parent_surrogate.pid,
            command_port_override=fake_command_port,
            registry_dir=isolated_registry_dir,
            open_command_port=False,  # we already spawned a fake listener
        )
        try:
            entry = _wait_for_registry_row(isolated_registry_dir)
            assert entry["dcc_type"] == "maya"
            assert entry["pid"] == parent_surrogate.pid, (
                "FileRegistry row's pid must equal the parent we asked the "
                "sidecar to watch — that lets sweepers correlate dead Maya "
                "PIDs with their orphaned sidecar rows."
            )
            metadata = entry.get("metadata") or {}
            assert metadata.get("dcc_mcp_role") == "per-dcc-sidecar"
            assert metadata.get("host_rpc_uri") == handle.host_rpc_uri
            assert handle.is_alive
        finally:
            stop_sidecar(handle, close_command_port=False)

        rc = _wait_for_proc_exit(handle)
        assert rc is not None
        # `stop_sidecar` is idempotent.
        stop_sidecar(handle, close_command_port=False)

    def test_ppid_watch_exits_when_parent_dies(
        self,
        parent_surrogate: _ParentSurrogate,
        fake_command_port: int,
        isolated_registry_dir: Path,
    ) -> None:
        handle = start_sidecar(
            maya_pid=parent_surrogate.pid,
            command_port_override=fake_command_port,
            registry_dir=isolated_registry_dir,
            open_command_port=False,
        )
        _wait_for_registry_row(isolated_registry_dir)

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
                for entry in _iter_entries(payload)
                if (entry.get("metadata") or {}).get("dcc_mcp_role")
                == "per-dcc-sidecar"
            ]
            assert survivors == [], (
                "PPID-watch shutdown path must deregister the sidecar; "
                f"found survivors: {survivors}"
            )

    def test_extra_args_propagate_to_sidecar(
        self,
        parent_surrogate: _ParentSurrogate,
        fake_command_port: int,
        isolated_registry_dir: Path,
    ) -> None:
        handle = start_sidecar(
            maya_pid=parent_surrogate.pid,
            command_port_override=fake_command_port,
            registry_dir=isolated_registry_dir,
            extra_args=[
                "--display-name",
                "Maya-Test",
                "--adapter-version",
                "0.0.0-test",
            ],
            open_command_port=False,
        )
        try:
            entry = _wait_for_registry_row(isolated_registry_dir)
            assert entry.get("display_name") == "Maya-Test"
            assert entry.get("adapter_version") == "0.0.0-test"
            assert entry.get("adapter_dcc") == "maya"
        finally:
            stop_sidecar(handle, close_command_port=False)
            _wait_for_proc_exit(handle)

    def test_handle_carries_resolved_metadata(
        self,
        parent_surrogate: _ParentSurrogate,
        fake_command_port: int,
        isolated_registry_dir: Path,
    ) -> None:
        handle = start_sidecar(
            maya_pid=parent_surrogate.pid,
            command_port_override=fake_command_port,
            registry_dir=isolated_registry_dir,
            open_command_port=False,
        )
        try:
            assert handle.command_port == fake_command_port
            assert handle.host_rpc_uri == build_host_rpc_uri(fake_command_port)
            assert handle.maya_pid == parent_surrogate.pid
            assert handle.binary_path.exists()
            assert handle.is_alive
        finally:
            stop_sidecar(handle, close_command_port=False)
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
        tmp_path: Path,
    ) -> None:
        bogus = tmp_path / "does-not-exist"
        monkeypatch.setenv(ENV_SIDECAR_BINARY, str(bogus))
        # Make sure neither shutil.which nor the dcc_mcp_server package
        # accidentally rescue us during the test.
        monkeypatch.setenv("PATH", str(tmp_path))
        monkeypatch.setitem(__import__("sys").modules, "dcc_mcp_server", None)

        with pytest.raises(SidecarBinaryError) as exc_info:
            resolve_sidecar_binary()

        message = str(exc_info.value)
        assert ENV_SIDECAR_BINARY in message
        assert "shutil.which" in message
        assert "Install" in message  # documents the fix


# ── manual operator override smoke test ──────────────────────────────


def test_env_override_via_os_environ(
    parent_surrogate: _ParentSurrogate,
    fake_command_port: int,
    isolated_registry_dir: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Confirm that setting :data:`ENV_SIDECAR_BINARY` is enough for the
    Maya plug-in entry point to find the binary even when neither the
    PyPI wheel nor PATH is configured."""
    actual_binary = resolve_sidecar_binary()
    monkeypatch.setenv(ENV_SIDECAR_BINARY, str(actual_binary))
    monkeypatch.setenv("PATH", "")
    monkeypatch.setitem(os.sys.modules, "dcc_mcp_server", None)

    handle = start_sidecar(
        maya_pid=parent_surrogate.pid,
        command_port_override=fake_command_port,
        registry_dir=isolated_registry_dir,
        open_command_port=False,
    )
    try:
        _wait_for_registry_row(isolated_registry_dir)
        assert handle.binary_path == actual_binary
    finally:
        stop_sidecar(handle, close_command_port=False)
        _wait_for_proc_exit(handle)
