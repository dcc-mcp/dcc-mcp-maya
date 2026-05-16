"""Session-scope stdout/stderr capture for Maya — single ``action``-multiplexed tool.

Same shape as PatrickPalmer/maya-mcp-server's ``install_stream_capture`` /
``uninstall_stream_capture`` / ``get_buffered_output`` trio, collapsed
into one tool with an ``action`` selector. Reduces the public MCP
surface from 3 tools to 1 (RFC #998 follow-up direction: minimise tool
count, push behaviour into parameters).

Lifecycle
=========

``install``
    Replace ``sys.stdout`` / ``sys.stderr`` with tee writers that record
    everything **and** still forward to the original streams (so the
    user can see prints in Maya's Script Editor while the agent reads
    the buffer). Idempotent — calling twice does not stack writers.

``get``
    Return the buffered stdout / stderr accumulated since the last
    ``get`` / ``clear`` call (or since ``install``). By default the
    buffer is **drained** on read; pass ``drain=False`` to peek without
    consuming.

``clear``
    Empty the buffers without uninstalling.

``uninstall``
    Restore the original ``sys.stdout`` / ``sys.stderr`` writers and
    drop any buffered content.

``status``
    Report whether capture is currently installed and how many bytes
    are buffered, without touching them.

Persistent across calls
=======================

The tee writer is module-level state; an agent can ``install`` once at
the start of a session, run many ``execute_python`` calls (the
``capture_output=False`` argument frees them from per-call capture
overhead), and ``get`` the merged output between checkpoints. Same
session-level ergonomics as maya-mcp-server.

Why session-scope rather than per-call?
=======================================

``execute_python`` already takes ``capture_output`` for the per-call
case. ``io`` exists for the **other** workflow: drive a long-running
session, accumulate output across many small calls, drain it on
demand. The cumulative buffer is what makes "run 30 cmds.poly* calls
then ``io(action=get)``" cheaper than 30 separate envelope round-trips
each carrying a few lines of stdout.
"""

from __future__ import annotations

import io
import sys
import threading
from typing import Any, Optional, TextIO

from dcc_mcp_core.skill import skill_entry, skill_error, skill_success

_LOCK = threading.Lock()
_STATE = {
    "installed": False,
    "stdout_orig": None,
    "stderr_orig": None,
    "stdout_buf": io.StringIO(),
    "stderr_buf": io.StringIO(),
}


class _Tee:
    """Write to a buffer **and** forward to the real stream.

    Tolerates broken downstream sinks because Maya's Script Editor
    stream can vanish under DCC teardown, and we should not poison the
    dispatcher with the resulting ``ValueError`` on a closed stream.
    """

    def __init__(self, original: Optional[TextIO], buffer: io.StringIO) -> None:
        self._original = original
        self._buffer = buffer

    def write(self, text: str) -> int:
        if text:
            self._buffer.write(text)
        if self._original is not None:
            try:
                self._original.write(text)
            except Exception:  # noqa: BLE001 — Script Editor may be torn down
                pass
        return len(text) if text else 0

    def flush(self) -> None:
        if self._original is not None:
            try:
                self._original.flush()
            except Exception:  # noqa: BLE001
                pass

    def isatty(self) -> bool:
        return False


def _install_locked() -> dict:
    if _STATE["installed"]:
        return {
            "installed": False,
            "reused": True,
            "stdout_bytes": len(_STATE["stdout_buf"].getvalue()),
            "stderr_bytes": len(_STATE["stderr_buf"].getvalue()),
        }
    _STATE["stdout_orig"] = sys.stdout
    _STATE["stderr_orig"] = sys.stderr
    _STATE["stdout_buf"] = io.StringIO()
    _STATE["stderr_buf"] = io.StringIO()
    sys.stdout = _Tee(_STATE["stdout_orig"], _STATE["stdout_buf"])  # type: ignore[assignment]
    sys.stderr = _Tee(_STATE["stderr_orig"], _STATE["stderr_buf"])  # type: ignore[assignment]
    _STATE["installed"] = True
    return {"installed": True, "reused": False}


def _uninstall_locked() -> dict:
    if not _STATE["installed"]:
        return {"uninstalled": False, "was_installed": False}
    if _STATE["stdout_orig"] is not None:
        sys.stdout = _STATE["stdout_orig"]  # type: ignore[assignment]
    if _STATE["stderr_orig"] is not None:
        sys.stderr = _STATE["stderr_orig"]  # type: ignore[assignment]
    _STATE["installed"] = False
    _STATE["stdout_orig"] = None
    _STATE["stderr_orig"] = None
    return {"uninstalled": True, "was_installed": True}


def _get_locked(drain: bool) -> dict:
    stdout = _STATE["stdout_buf"].getvalue()
    stderr = _STATE["stderr_buf"].getvalue()
    if drain:
        _STATE["stdout_buf"] = io.StringIO()
        _STATE["stderr_buf"] = io.StringIO()
        if _STATE["installed"]:
            sys.stdout = _Tee(_STATE["stdout_orig"], _STATE["stdout_buf"])  # type: ignore[assignment]
            sys.stderr = _Tee(_STATE["stderr_orig"], _STATE["stderr_buf"])  # type: ignore[assignment]
    return {
        "stdout": stdout,
        "stderr": stderr,
        "drained": drain,
        "installed": _STATE["installed"],
    }


def _clear_locked() -> dict:
    _STATE["stdout_buf"] = io.StringIO()
    _STATE["stderr_buf"] = io.StringIO()
    if _STATE["installed"]:
        sys.stdout = _Tee(_STATE["stdout_orig"], _STATE["stdout_buf"])  # type: ignore[assignment]
        sys.stderr = _Tee(_STATE["stderr_orig"], _STATE["stderr_buf"])  # type: ignore[assignment]
    return {"cleared": True, "installed": _STATE["installed"]}


def _status_locked() -> dict:
    return {
        "installed": _STATE["installed"],
        "stdout_bytes": len(_STATE["stdout_buf"].getvalue()),
        "stderr_bytes": len(_STATE["stderr_buf"].getvalue()),
    }


_ACTIONS = {
    "install": lambda _params: _install_locked(),
    "uninstall": lambda _params: _uninstall_locked(),
    "get": lambda params: _get_locked(bool(params.get("drain", True))),
    "clear": lambda _params: _clear_locked(),
    "status": lambda _params: _status_locked(),
}


def io_action(**params: Any):
    """Single action-multiplexed entry point for stdout / stderr capture.

    The ``action`` parameter is required and must be one of
    ``install`` / ``uninstall`` / ``get`` / ``clear`` / ``status``.
    """
    action = str(params.get("action", "")).strip().lower()
    if not action:
        return skill_error(
            "`action` parameter is required",
            "Pass one of: " + ", ".join(sorted(_ACTIONS)),
        )
    handler = _ACTIONS.get(action)
    if handler is None:
        return skill_error(
            "Unknown action {0!r}".format(action),
            "Allowed: " + ", ".join(sorted(_ACTIONS)),
        )
    with _LOCK:
        payload = handler(params)
    return skill_success(
        "io action {0!r} completed".format(action),
        prompt="See context.* for buffered output / status.",
        action=action,
        **payload,
    )


@skill_entry
def main(**kwargs) -> dict:
    """Skill entry — delegates to :func:`io_action`."""
    return io_action(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
