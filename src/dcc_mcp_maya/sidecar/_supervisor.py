"""Subprocess supervision for the ``dcc-mcp-server sidecar`` binary.

The Maya plug-in entry point calls :func:`start_sidecar` once Maya's
main thread is idle, and :func:`stop_sidecar` from ``uninitializePlugin``.
All Maya-specific concerns (opening ``cmds.commandPort``, deferring
startup until the UI is responsive) live in the plug-in file —
this module is **pure stdlib + subprocess** so the supervision logic
is testable without a real Maya.

Design choices worth pinning:

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

from dcc_mcp_maya.sidecar._commandport import allocate_free_port, build_host_rpc_uri
from dcc_mcp_maya.sidecar._resolver import (
    SidecarBinaryError,
    resolve_sidecar_binary,
)

__all__ = [
    "ENV_SIDECAR_MODE",
    "SidecarHandle",
    "SidecarSpawnError",
    "is_sidecar_mode_enabled",
    "start_sidecar",
    "stop_sidecar",
]

logger = logging.getLogger(__name__)

ENV_SIDECAR_MODE = "DCC_MCP_MAYA_SIDECAR"
_TRUTHY_VALUES = frozenset({"1", "true", "yes", "on"})

# Grace period before SIGKILL on shutdown. 5 s matches the sidecar
# binary's own ``--shutdown-timeout-secs`` default; cap at the same
# value so the Maya plug-in unload never blocks longer than the binary
# would take to exit on its own.
_DEFAULT_TERMINATE_GRACE_SECS = 5.0


class SidecarSpawnError(RuntimeError):
    """Raised when :func:`start_sidecar` cannot launch the binary.

    Wraps the underlying cause (missing binary, port allocation
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
    command_port: int
    host_rpc_uri: str
    binary_path: Path
    maya_pid: int
    extra_env: dict[str, str] = field(default_factory=dict)

    @property
    def is_alive(self) -> bool:
        """Whether the sidecar subprocess is still running."""
        return self.proc.poll() is None


def is_sidecar_mode_enabled(env: Optional[dict[str, str]] = None) -> bool:
    """Return ``True`` when sidecar mode is opted-in via the env var.

    Args:
        env: optional environment-variable mapping to consult. Defaults
            to :data:`os.environ`. Exposed for tests so the gate can be
            exercised without mutating the live process environment.
    """
    raw = (env if env is not None else os.environ).get(ENV_SIDECAR_MODE, "")
    return raw.strip().lower() in _TRUTHY_VALUES


def start_sidecar(
    *,
    maya_pid: Optional[int] = None,
    dcc_name: str = "maya",
    binary_override: Optional[Path] = None,
    command_port_override: Optional[int] = None,
    registry_dir: Optional[Path] = None,
    display_name: Optional[str] = None,
    adapter_version: Optional[str] = None,
    extra_args: Optional[list[str]] = None,
    extra_env: Optional[dict[str, str]] = None,
    open_command_port: bool = True,
) -> SidecarHandle:
    """Open Maya's ``commandPort`` and spawn the sidecar subprocess.

    Args:
        maya_pid: PID for the sidecar's ``--watch-pid`` flag. Defaults to
            the current process (i.e. Maya's PID when called from
            ``initializePlugin``).
        dcc_name: ``--dcc`` flag value. Stays ``"maya"`` for this plug-in
            but exposed for tests that simulate other DCCs.
        binary_override: explicit binary path. Bypasses
            :func:`resolve_sidecar_binary` when set; useful for tests.
        command_port_override: explicit commandPort to use. When ``None``
            (the production path) an ephemeral port is allocated via
            :func:`allocate_free_port`.
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
        open_command_port: when ``True`` (default), import
            ``maya.cmds`` and open ``commandPort`` on the chosen port.
            Tests pass ``False`` so the function can be exercised
            without a Maya runtime — they bring their own listener.

    Returns:
        A :class:`SidecarHandle` referencing the spawned subprocess.

    Raises:
        SidecarSpawnError: when binary resolution, commandPort opening,
            or ``subprocess.Popen`` itself fails.
    """
    if maya_pid is None:
        maya_pid = os.getpid()

    try:
        binary = binary_override or resolve_sidecar_binary()
    except SidecarBinaryError as exc:
        raise SidecarSpawnError(str(exc)) from exc

    port = command_port_override or allocate_free_port()
    host_rpc_uri = build_host_rpc_uri(port)

    if open_command_port:
        _open_maya_command_port(port)

    cmd: list[str] = [
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
    if extra_args:
        cmd.extend(extra_args)

    spawn_env = os.environ.copy()
    if extra_env:
        spawn_env.update(extra_env)

    logger.info(
        "dcc-mcp-maya: spawning sidecar %s (port=%d, watch_pid=%d)",
        binary,
        port,
        maya_pid,
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
        if open_command_port:
            _close_maya_command_port_quiet(port)
        raise SidecarSpawnError(
            f"failed to spawn dcc-mcp-server sidecar at {binary}: {exc}"
        ) from exc

    return SidecarHandle(
        proc=proc,
        command_port=port,
        host_rpc_uri=host_rpc_uri,
        binary_path=binary,
        maya_pid=maya_pid,
        extra_env=dict(extra_env or {}),
    )


def stop_sidecar(
    handle: SidecarHandle,
    *,
    grace_secs: float = _DEFAULT_TERMINATE_GRACE_SECS,
    close_command_port: bool = True,
) -> None:
    """Terminate the sidecar subprocess and (optionally) close commandPort.

    Idempotent: safe to call multiple times. If the subprocess already
    exited (e.g. PPID-watch fired because Maya was tearing down), only
    the commandPort cleanup runs.

    Args:
        handle: the value returned by :func:`start_sidecar`.
        grace_secs: how long to wait for graceful exit before
            ``SIGKILL``-ing the process. ``5.0`` mirrors the sidecar
            binary's own shutdown timeout default.
        close_command_port: whether to call ``cmds.commandPort(close=True)``.
            Tests that did not open a real commandPort should pass
            ``False``.
    """
    if handle.proc.poll() is None:
        try:
            handle.proc.terminate()
        except OSError as exc:  # noqa: BLE001
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
            except OSError as exc:  # noqa: BLE001
                logger.debug("sidecar kill() raised: %s", exc)
            try:
                handle.proc.wait(timeout=2.0)
            except subprocess.TimeoutExpired:
                logger.error(
                    "dcc-mcp-maya: sidecar PID %s still alive after kill",
                    handle.proc.pid,
                )

    if close_command_port:
        _close_maya_command_port_quiet(handle.command_port)


# ── internal helpers ──────────────────────────────────────────────


def _open_maya_command_port(port: int) -> None:
    """Open Maya's ``commandPort`` on the given TCP port.

    Imported lazily so the module stays importable from CI / pytest
    without Maya being installed.
    """
    try:
        import maya.cmds as cmds  # type: ignore[import-not-found]
    except ImportError as exc:
        raise SidecarSpawnError(
            "open_command_port=True but maya.cmds is not importable — "
            "are we running inside Maya?"
        ) from exc

    name = f":{port}"
    try:
        if cmds.commandPort(name, query=True):
            cmds.commandPort(name=name, close=True)
    except Exception:  # noqa: BLE001 — query may return failure on Maya 2020
        pass

    try:
        cmds.commandPort(name=name, sourceType="python", noreturn=False)
    except Exception as exc:  # noqa: BLE001
        raise SidecarSpawnError(
            f"cmds.commandPort failed to open port {port}: {exc}"
        ) from exc


def _close_maya_command_port_quiet(port: int) -> None:
    """Close commandPort without propagating exceptions.

    Best-effort cleanup invoked from teardown paths that must succeed
    even when Maya is mid-shutdown.
    """
    try:
        import maya.cmds as cmds  # type: ignore[import-not-found]
    except ImportError:
        return
    name = f":{port}"
    try:
        if cmds.commandPort(name, query=True):
            cmds.commandPort(name=name, close=True)
    except Exception as exc:  # noqa: BLE001
        logger.debug("commandPort %s close failed: %s", name, exc)


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
