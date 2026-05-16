"""Capture Maya's native Script Editor output (issue #151).

Python's ``sys.stdout`` / ``sys.stderr`` capture only covers ``print()``
and any code that writes to those streams directly. MEL ``print``,
``cmds.warning``, ``cmds.error`` and ``cmds.displayInfo`` are emitted
through Maya's C++ ``MCommandMessage`` channel and never touch Python's
stdout — so the previous ``ScriptExecutionCapture``-only approach left
these messages invisible to MCP clients (issue #151).

:class:`MayaOutputCapture` wraps
``OpenMaya.MCommandMessage.addCommandOutputCallback`` to funnel these
messages into an in-memory buffer during a ``with`` block.

Stability note (RFC #998 follow-up 2026-05-16)
==============================================

``MCommandMessage.addCommandOutputCallback`` is a **C++ → Python
callback bridge** on Maya's main thread. The same family of bugs that
forced removal of the ``cmds.confirmDialog`` monkey-patch in
``_safe_session.py`` applies here:

* Maya's C++ side may queue command-output messages on an internal
  pump that fires on the next idle tick.
* When our ``__exit__`` calls ``MMessage.removeCallback`` after a
  dispatch returns, any messages the engine had already enqueued but
  not yet delivered now reference an invalid Python callback.
* On the next idle tick Maya derefs the cleared callback slot and
  SEGV's the process — **after** the dispatch has already returned
  ``success`` to the MCP client (exactly the failure pattern we
  observed running ``cmds.file(new=True)`` + ``cmds.render`` user
  scripts).

The fix is to default this capture **off** and require operators to
opt in via ``DCC_MCP_MAYA_HOOK_MAYA_OUTPUT=1`` for the rare case where
they explicitly want ``cmds.warning`` / ``cmds.error`` mirrored into
the MCP envelope. ``ScriptExecutionCapture(tee=True)`` (which only
redirects ``sys.stdout`` / ``sys.stderr``) remains the always-on
default — it covers every ``print()`` from user code and the script-
editor mirror that Maya itself injects via Python's stdout. The
information lost by disabling the OpenMaya hook is the C++-only
``cmds.warning`` / ``cmds.displayInfo`` messages; user-facing errors
still propagate via the Python exception path captured by
``ScriptExecutionCapture``.

When ``DCC_MCP_MAYA_HOOK_MAYA_OUTPUT=1`` is set the original behaviour
is restored verbatim — the C++ callback is registered and removed
across the ``with`` block exactly as before. Operators who explicitly
need that channel and accept the crash risk can flip it back on.

Typical usage
-------------

The default path — no Maya callback hooks installed — is what every
skill should use. Pass ``hook_maya_output=True`` to opt back into the
C++ callback bridge for a specific call site that has been
established as safe (e.g. a unit test running in mayapy under a
controlled scene).

See: https://github.com/loonghao/dcc-mcp-maya/issues/151
"""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging
import os
from typing import Any, List, Optional

__all__ = ["MayaOutputCapture", "is_maya_output_hook_enabled"]

_LOG = logging.getLogger(__name__)

# MCommandMessage output-type constants (mirror the OpenMaya enum values
# so we can classify messages without keeping a live import around).
# Values are stable across supported Maya versions.
_MSG_TYPE_INFO = 1  # kInfo
_MSG_TYPE_WARNING = 2  # kWarning
_MSG_TYPE_ERROR = 3  # kError
_MSG_TYPE_RESULT = 4  # kResult
_MSG_TYPE_STACK_TRACE = 5  # kStackTrace


ENV_HOOK_MAYA_OUTPUT = "DCC_MCP_MAYA_HOOK_MAYA_OUTPUT"


def is_maya_output_hook_enabled() -> bool:
    """Return ``True`` when operators have opted into the OpenMaya callback hook.

    Default is ``False`` because installing the
    ``MCommandMessage.addCommandOutputCallback`` bridge crashes Maya
    on common scripts that leave pending command-output messages in
    the engine's idle queue (see the stability note in the module
    docstring). Operators who explicitly need ``cmds.warning`` /
    ``cmds.error`` mirrored into the MCP envelope can opt in by
    setting ``DCC_MCP_MAYA_HOOK_MAYA_OUTPUT=1`` (also accepts
    ``true`` / ``on`` / ``yes``).
    """
    raw = os.environ.get(ENV_HOOK_MAYA_OUTPUT, "").strip().lower()
    return raw in {"1", "true", "on", "yes"}


def _load_openmaya() -> Optional[Any]:
    """Return ``maya.api.OpenMaya``, or ``None`` when Maya is unavailable."""
    try:
        from maya.api import OpenMaya as _om  # noqa: PLC0415

        return _om
    except Exception:  # noqa: BLE001 — any import-time failure should degrade
        return None


class MayaOutputCapture:
    """Context manager capturing Maya's ``MCommandMessage`` output.

    Attributes
    ----------
    stdout : str
        Messages classified as ``kInfo`` / ``kResult`` (human-facing
        stdout-equivalent lines).
    stderr : str
        Messages classified as ``kWarning`` / ``kError`` /
        ``kStackTrace``. Warnings and errors are grouped here so MCP
        clients can surface them in a failure panel.

    The capture is a **best-effort** helper: if Maya's Python API is not
    importable, both attributes remain empty strings and entering /
    exiting the context is a no-op. This keeps unit tests that run
    without a live Maya session from needing any special mocking.

    Defaults to a **no-op** for stability — registering the C++
    callback bridge crashes Maya on common user scripts (see the
    module docstring). Operators who explicitly need the
    ``MCommandMessage`` channel can opt in via
    ``DCC_MCP_MAYA_HOOK_MAYA_OUTPUT=1``. Callers that have audited
    their specific use case can also pass ``force=True`` to bypass
    the env-var gate for a single call site.
    """

    def __init__(self, *, force: bool = False) -> None:
        self._om: Optional[Any] = None
        self._callback_id: Optional[Any] = None
        self._stdout_buf: List[str] = []
        self._stderr_buf: List[str] = []
        self._force = bool(force)

    # ------------------------------------------------------------------
    # Results
    # ------------------------------------------------------------------
    @property
    def stdout(self) -> str:
        """All captured info / result lines joined by newlines."""
        return "\n".join(self._stdout_buf) + ("\n" if self._stdout_buf else "")

    @property
    def stderr(self) -> str:
        """All captured warning / error / stack-trace lines."""
        return "\n".join(self._stderr_buf) + ("\n" if self._stderr_buf else "")

    # ------------------------------------------------------------------
    # Context protocol
    # ------------------------------------------------------------------
    def __enter__(self) -> "MayaOutputCapture":
        if not (self._force or is_maya_output_hook_enabled()):
            # Default no-op path. The OpenMaya callback bridge crashes
            # Maya on common idle-tick interactions (see module
            # docstring); operators must opt in explicitly.
            return self

        self._om = _load_openmaya()
        if self._om is None:
            return self  # no-op fallback

        try:
            self._callback_id = self._om.MCommandMessage.addCommandOutputCallback(self._on_output)
        except Exception as exc:  # noqa: BLE001 — degrade silently, log at debug
            _LOG.debug("MayaOutputCapture: callback registration failed: %s", exc)
            self._callback_id = None
        return self

    def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        if self._callback_id is None or self._om is None:
            return
        try:
            self._om.MMessage.removeCallback(self._callback_id)
        except Exception as unregister_exc:  # noqa: BLE001
            _LOG.debug(
                "MayaOutputCapture: callback removal failed: %s",
                unregister_exc,
            )
        finally:
            self._callback_id = None

    # ------------------------------------------------------------------
    # Callback
    # ------------------------------------------------------------------
    def _on_output(self, message: str, message_type: int, _client_data: Any = None) -> None:
        """``MCommandMessage`` callback: route by message type.

        The optional ``client_data`` parameter is ignored when Maya supplies it.
        """
        try:
            text = str(message)
        except Exception:  # noqa: BLE001
            return

        if message_type in (_MSG_TYPE_INFO, _MSG_TYPE_RESULT):
            self._stdout_buf.append(text)
        else:
            # Warnings, errors, stack traces all land in stderr so MCP
            # clients can present them as failures.  We do not attempt
            # to further subdivide the buffer because the structured
            # envelope already surfaces ``message_type`` via the
            # traceback field when an exception is raised.
            self._stderr_buf.append(text)
