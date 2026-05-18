"""Subprocess supervision for the ``dcc-mcp-server sidecar`` binary.

The Maya plug-in entry point calls :func:`start_sidecar` once Maya's
main thread is idle, and :func:`stop_sidecar` from
``uninitializePlugin``. The supervisor:

1. Eagerly starts the universal in-DCC **Qt event-loop dispatcher**
   (see :mod:`dcc_mcp_maya.sidecar._qt_dispatcher`) inside Maya itself,
   so an external sidecar binary never needs ``commandPort`` to
   bootstrap the wire. The dispatcher binds an ephemeral TCP port via
   ``QTcpServer`` and runs cooperatively on Maya's own Qt event loop —
   structurally immune to the single-flight / modal-dialog / PyO3-tokio
   contention failure modes the legacy ``commandPort`` path suffered
   from (RFC #998 Addendum B).

2. Registers a ``dispatch`` handler on the Qt dispatcher's registry
   that forwards JSON wire frames to the existing Maya-side action
   dispatcher (:mod:`dcc_mcp_maya.sidecar._dispatcher`). The Qt server
   becomes the transport, but the action-lookup contract stays
   identical to the in-process path.

3. Spawns the ``dcc-mcp-server sidecar`` subprocess with
   ``--host-rpc qtserver://...`` so the binary connects back to the
   Maya-hosted Qt server. The binary runs alongside Maya, supervised
   by its PPID-watch, and survives non-cooperative Maya shutdowns so
   the gateway can emit structured ``host-died`` envelopes instead of
   transport-error cascades.

Design choices worth pinning:

* **No commandPort.** The legacy ``commandPort`` path is gone — see
  RFC #998 Addendum B (item 2). Qt dispatcher solves the same need
  with multi-client concurrency and ``try/except``-per-request safety.
* **PPID-watch lives in the sidecar binary, not here.** The binary's
  ``sidecar`` subcommand polls ``--watch-pid`` every 250 ms and exits
  cleanly when the parent dies (verified end-to-end by the integration
  test in ``dcc-mcp-core`` PR #1003). The Python side just provides
  the PID and lets the binary self-supervise.
* **Sidecar is NOT detached.** It is a real child process of Maya,
  inheriting Maya's process tree. When Maya exits the OS reaps the
  sidecar naturally as a backstop in case PPID-watch was somehow
  bypassed.
* **No raw ``log to stderr`` plumbing** — the binary writes structured
  logs to ``DCC_MCP_LOG_DIR`` already (see
  ``dcc-mcp-logging::file_logging``). The Python plug-in shouldn't
  duplicate that.
"""

from __future__ import annotations

import logging
import os
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from dcc_mcp_maya.sidecar._resolver import (
    SidecarBinaryError,
    resolve_sidecar_binary,
)

__all__ = [
    "ENV_SIDECAR_MODE",
    "SidecarHandle",
    "SidecarSpawnError",
    "build_qtserver_uri",
    "is_sidecar_mode_enabled",
    "start_sidecar",
    "stop_sidecar",
]

logger = logging.getLogger(__name__)

ENV_SIDECAR_MODE = "DCC_MCP_MAYA_SIDECAR"
_TRUTHY_VALUES = frozenset({"1", "true", "yes", "on"})
_FALSEY_VALUES = frozenset({"0", "false", "no", "off"})

# Grace period before SIGKILL on shutdown. 5 s matches the sidecar
# binary's own ``--shutdown-timeout-secs`` default; cap at the same
# value so the Maya plug-in unload never blocks longer than the binary
# would take to exit on its own.
_DEFAULT_TERMINATE_GRACE_SECS = 5.0


class SidecarSpawnError(RuntimeError):
    """Raised when :func:`start_sidecar` cannot launch the binary.

    Wraps the underlying cause (missing binary, Qt server start
    failure, ``OSError`` from ``subprocess.Popen``) so callers in the
    plug-in entry point can log a single structured error and fall
    back to in-process mode silently.
    """


@dataclass(frozen=True)
class SidecarHandle:
    """Lifetime handle returned by :func:`start_sidecar`.

    Pass back to :func:`stop_sidecar` from ``uninitializePlugin``.
    Fields are public so debug tooling / smoke tests can inspect them
    without going through the plug-in entry point.
    """

    proc: subprocess.Popen
    qt_port: int
    qt_binding: str
    host_rpc_uri: str
    binary_path: Path
    maya_pid: int
    extra_env: dict = field(default_factory=dict)

    @property
    def is_alive(self) -> bool:
        """Whether the sidecar subprocess is still running."""
        return self.proc.poll() is None


def build_qtserver_uri(port: int, host: str = "127.0.0.1") -> str:
    """Format the ``qtserver://`` URI the sidecar binary will dial.

    The scheme is the discriminator the Rust router in
    ``dcc-mcp-host-rpc`` matches on to pick the ``QtServerClient``
    impl. Keep it lowercase and stable.

    Args:
        port: TCP port the in-Maya ``QTcpServer`` bound to (announced
            by :func:`_qt_dispatcher.start_qt_server`).
        host: bind address. Defaults to loopback.

    Raises:
        ValueError: when ``port`` is outside ``1..65535``.

    Returns:
        URI of the form ``"qtserver://127.0.0.1:18765"``.
    """
    if port <= 0 or port > 65535:
        raise ValueError("port must be in 1..65535, got {0}".format(port))
    return "qtserver://{0}:{1}".format(host, port)


def is_sidecar_mode_enabled(env: Optional[dict] = None) -> bool:
    """Return ``True`` unless sidecar mode is explicitly disabled.

    Args:
        env: optional environment-variable mapping to consult. Defaults
            to :data:`os.environ`. Exposed for tests so the gate can be
            exercised without mutating the live process environment.
    """
    raw = (env if env is not None else os.environ).get(ENV_SIDECAR_MODE)
    if raw is None or not raw.strip():
        return True
    normalized = raw.strip().lower()
    if normalized in _FALSEY_VALUES:
        return False
    # Unknown values preserve the default-on behaviour; only explicit
    # falsey tokens opt out.
    return True


def start_sidecar(
    *,
    maya_pid: Optional[int] = None,
    dcc_name: str = "maya",
    binary_override: Optional[Path] = None,
    qt_port_override: Optional[int] = None,
    registry_dir: Optional[Path] = None,
    display_name: Optional[str] = None,
    adapter_version: Optional[str] = None,
    extra_args: Optional[list] = None,
    extra_env: Optional[dict] = None,
    start_qt_server_fn=None,
    stop_qt_server_fn=None,
) -> SidecarHandle:
    """Start the in-Maya Qt dispatcher and spawn the sidecar subprocess.

    Args:
        maya_pid: PID for the sidecar's ``--watch-pid`` flag. Defaults to
            the current process (i.e. Maya's PID when called from
            ``initializePlugin``).
        dcc_name: ``--dcc`` flag value. Stays ``"maya"`` for this plug-in
            but exposed for tests that simulate other DCCs.
        binary_override: explicit binary path. Bypasses
            :func:`resolve_sidecar_binary` when set; useful for tests.
        qt_port_override: pin the Qt server to a specific TCP port. When
            ``None`` (the production path) ``QTcpServer`` picks an
            ephemeral port and announces it via the function's return.
            Tests use a known port to drive deterministic assertions.
        registry_dir: passed through to ``--registry-dir``. Defaults to
            the binary's own platform-specific location.
        display_name: human-readable label written to the FileRegistry
            row (``--display-name``). Useful when multiple Maya sessions
            share a host and an agent needs to disambiguate.
        adapter_version: ``dcc_mcp_maya`` package version stamped onto
            the row (``--adapter-version``). The plug-in passes its own
            ``VERSION`` here so gateway election can rank adapter
            generations (see issue maya#137).
        extra_args: additional CLI args appended after the standard set.
            For one-off flags that do not deserve a first-class kwarg.
        extra_env: environment overrides for the subprocess. Merged on
            top of :data:`os.environ` so the sidecar inherits Maya's
            existing ``DCC_MCP_*`` settings.
        start_qt_server_fn: dependency-injection seam for tests. When
            ``None`` (production) imports the vendored
            :mod:`dcc_mcp_maya.sidecar._qt_dispatcher` and calls its
            :func:`start_qt_server`. Tests pass a stub that returns a
            canned ``{"host", "port", "qt_binding"}`` dict so the
            supervisor can be exercised without a Qt runtime.
        stop_qt_server_fn: companion teardown hook used if startup fails
            after the Qt server has already been started.

    Returns:
        A :class:`SidecarHandle` referencing the spawned subprocess.

    Raises:
        SidecarSpawnError: when binary resolution, Qt server start, or
            ``subprocess.Popen`` itself fails.
    """
    if maya_pid is None:
        maya_pid = os.getpid()

    try:
        binary = binary_override or resolve_sidecar_binary()
    except SidecarBinaryError as exc:
        raise SidecarSpawnError(str(exc)) from exc

    requested_port = qt_port_override if qt_port_override is not None else 0
    qt_info = _start_qt_server(requested_port, start_qt_server_fn)
    qt_port = int(qt_info["port"])
    qt_host = str(qt_info.get("host", "127.0.0.1"))
    qt_binding = str(qt_info.get("qt_binding", "unknown"))

    try:
        _register_dispatch_handler(start_qt_server_fn)
    except Exception as exc:  # noqa: BLE001 — narrow it to SidecarSpawnError
        _stop_qt_server(stop_qt_server_fn)
        raise SidecarSpawnError(
            "failed to register `dispatch` handler on the in-Maya Qt server: {0}".format(exc)
        ) from exc

    host_rpc_uri = build_qtserver_uri(qt_port, host=qt_host)

    cmd = [
        str(binary),
        "sidecar",
        "--dcc",
        dcc_name,
        "--host-rpc",
        host_rpc_uri,
        "--watch-pid",
        str(maya_pid),
    ]
    if registry_dir is not None:
        cmd.extend(["--registry-dir", str(registry_dir)])
    if display_name is not None:
        cmd.extend(["--display-name", display_name])
    if adapter_version is not None:
        cmd.extend(["--adapter-version", adapter_version])
    gateway_port_str = os.environ.get("DCC_MCP_GATEWAY_PORT", "9765").strip()
    try:
        gateway_port = int(gateway_port_str)
    except ValueError:
        gateway_port = 9765
    if gateway_port > 0:
        cmd.extend(["--gateway-port", str(gateway_port)])
    if extra_args:
        cmd.extend(extra_args)

    spawn_env = os.environ.copy()
    if extra_env:
        spawn_env.update(extra_env)

    logger.info(
        "dcc-mcp-maya: spawning sidecar %s (qt_port=%d, watch_pid=%d, qt_binding=%s)",
        binary,
        qt_port,
        maya_pid,
        qt_binding,
    )
    try:
        proc = subprocess.Popen(  # noqa: S603 — argv is built from trusted vars
            cmd,
            env=spawn_env,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            close_fds=True,
            creationflags=_detached_process_flags(),
        )
    except OSError as exc:
        _stop_qt_server(stop_qt_server_fn)
        raise SidecarSpawnError("failed to spawn dcc-mcp-server sidecar at {0}: {1}".format(binary, exc)) from exc

    return SidecarHandle(
        proc=proc,
        qt_port=qt_port,
        qt_binding=qt_binding,
        host_rpc_uri=host_rpc_uri,
        binary_path=binary,
        maya_pid=maya_pid,
        extra_env=dict(extra_env or {}),
    )


def stop_sidecar(
    handle: SidecarHandle,
    *,
    grace_secs: float = _DEFAULT_TERMINATE_GRACE_SECS,
    stop_qt_server_fn=None,
) -> None:
    """Terminate the sidecar subprocess and tear down the in-Maya Qt server.

    Idempotent: safe to call multiple times. If the subprocess already
    exited (e.g. PPID-watch fired because Maya was tearing down), only
    the Qt server cleanup runs.

    Args:
        handle: the value returned by :func:`start_sidecar`.
        grace_secs: how long to wait for graceful exit before
            ``SIGKILL``-ing the process. ``5.0`` mirrors the sidecar
            binary's own shutdown timeout default.
        stop_qt_server_fn: dependency-injection seam for tests.
            When ``None`` (production) calls the vendored
            :func:`_qt_dispatcher.stop_qt_server`.
    """
    if handle.proc.poll() is None:
        try:
            handle.proc.terminate()
        except OSError as exc:
            logger.debug("sidecar terminate() raised: %s", exc)
        try:
            handle.proc.wait(timeout=grace_secs)
        except subprocess.TimeoutExpired:
            logger.warning(
                "dcc-mcp-maya: sidecar did not exit within %.1fs — killing",
                grace_secs,
            )
            try:
                handle.proc.kill()
            except OSError as exc:
                logger.debug("sidecar kill() raised: %s", exc)
            try:
                handle.proc.wait(timeout=2.0)
            except subprocess.TimeoutExpired:
                logger.error(
                    "dcc-mcp-maya: sidecar PID %s still alive after kill",
                    handle.proc.pid,
                )

    _stop_qt_server(stop_qt_server_fn)


# ── internal helpers ──────────────────────────────────────────────


def _start_qt_server(port, start_qt_server_fn):
    """Resolve the Qt dispatcher and start it on the given port.

    Lazy-imports the vendored dispatcher so this module stays
    importable from CI / pytest without a Qt binding being available.
    Tests can pass ``start_qt_server_fn`` to bypass the import.
    """
    if start_qt_server_fn is not None:
        return start_qt_server_fn(port=port)
    try:
        from dcc_mcp_maya.sidecar._qt_dispatcher import start_qt_server
    except ImportError as exc:
        raise SidecarSpawnError(
            "failed to import in-Maya Qt dispatcher (dcc_mcp_maya.sidecar._qt_dispatcher): {0}".format(exc)
        ) from exc
    try:
        return start_qt_server(port=port)
    except Exception as exc:  # noqa: BLE001 — narrow to SidecarSpawnError
        raise SidecarSpawnError("failed to start in-Maya Qt server on port {0}: {1}".format(port, exc)) from exc


def _stop_qt_server(stop_qt_server_fn):
    """Best-effort tear-down of the singleton Qt server.

    Mirrors :func:`_start_qt_server`: lazy import, exception-swallowing
    on failure because we run from teardown paths that must complete
    even when Maya is mid-shutdown.
    """
    if stop_qt_server_fn is not None:
        try:
            stop_qt_server_fn()
        except Exception as exc:  # noqa: BLE001
            logger.debug("custom stop_qt_server_fn raised: %s", exc)
        return
    try:
        from dcc_mcp_maya.sidecar._qt_dispatcher import stop_qt_server
    except ImportError as exc:
        logger.debug("qt dispatcher unavailable on teardown: %s", exc)
        return
    try:
        stop_qt_server()
    except Exception as exc:  # noqa: BLE001
        logger.debug("stop_qt_server raised: %s", exc)


def _register_dispatch_handler(start_qt_server_fn):
    """Install a ``dispatch`` method on the Qt server's registry.

    The Rust ``QtServerClient`` wraps every ``HostRpcClient::call``
    as a ``method="dispatch"`` JSON-line frame. We tie that wire
    method back to the existing Maya-side action dispatcher
    (:mod:`dcc_mcp_maya.sidecar._dispatcher`) so the dispatch contract
    is wire-format-agnostic — same action-lookup logic regardless of
    whether the caller is in-process, qtserver, or a future scheme.

    When ``start_qt_server_fn`` is non-None (test path), we skip the
    registration — tests assert the supervisor *attempted* to register
    via their stubbed ``start_qt_server_fn`` and exercise the dispatch
    contract in a separate test.
    """
    if start_qt_server_fn is not None:
        return
    try:
        from dcc_mcp_maya.sidecar import _qt_dispatcher
    except ImportError as exc:
        raise RuntimeError("vendored dispatcher missing: {0}".format(exc)) from exc
    from dcc_mcp_maya.sidecar._dispatcher import dispatch_payload

    server = _qt_dispatcher.current_server()
    if server is None:
        raise RuntimeError(
            "in-Maya Qt server is not running — start_qt_server returned without populating the singleton"
        )

    def _handle_dispatch(params):
        # The wire frame is `{"action", "args", "request_id"}` — see
        # the Rust QtServerClient::call wrapper. dispatch_payload
        # returns a JSON envelope dict; we return it as-is so the Qt
        # dispatcher wraps it into `{"id": ..., "result": <dict>}`.
        return dispatch_payload(params)

    server.registry.register("dispatch", _handle_dispatch)


def _detached_process_flags() -> int:
    """OS-specific creation flags for ``subprocess.Popen``.

    The sidecar is a regular child of Maya — we do NOT detach it on
    Windows. Detaching would defeat the OS-level backstop that reaps
    orphaned children when their parent dies. The PPID-watch in the
    binary is the primary supervision mechanism; OS reaping is the
    safety net.
    """
    if sys.platform == "win32":
        # CREATE_NO_WINDOW so the binary doesn't open a console window
        # behind Maya's UI; still inherits Maya's process tree.
        CREATE_NO_WINDOW = 0x0800_0000  # noqa: N806
        return CREATE_NO_WINDOW
    return 0


def _await_proc_alive(proc: subprocess.Popen, timeout: float = 0.5) -> bool:
    """Brief sanity check that the subprocess did not exit immediately.

    Returns ``True`` if the process is still alive after the timeout.
    Used by tests to confirm the spawn succeeded before asserting
    side effects like FileRegistry registration.
    """
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if proc.poll() is not None:
            return False
        time.sleep(0.025)
    return True
