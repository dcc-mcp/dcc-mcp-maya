"""Capture Maya's native Script Editor output (issue #151).

Python's ``sys.stdout`` / ``sys.stderr`` capture only covers ``print()``
and any code that writes to those streams directly.  MEL ``print``,
``cmds.warning``, ``cmds.error`` and ``cmds.displayInfo`` are emitted
through Maya's C++ ``MCommandMessage`` channel and never touch Python's
stdout — so the previous ``ScriptExecutionCapture``-only approach left
these messages invisible to MCP clients (issue #151).

:class:`MayaOutputCapture` wraps
``OpenMaya.MCommandMessage.addCommandOutputCallback`` to funnel these
messages into an in-memory buffer during a ``with`` block.  It is safe
to use outside Maya (e.g. plain ``pytest`` without ``maya.standalone``):
when ``maya.api.OpenMaya`` / ``maya.OpenMaya`` cannot be imported, the
context manager degrades to a **no-op** that simply records empty
buffers — matching the "lazy import inside the function" pattern the
skill scripts already use.

Typical usage
-------------

Stack on top of ``dcc_mcp_core.script_execution.ScriptExecutionCapture``
so that Python ``print()`` **and** Maya's ``cmds.warning(...)`` both
reach the MCP client:

.. code-block:: python

    from dcc_mcp_core.script_execution import ScriptExecutionCapture
    from dcc_mcp_maya._maya_output import MayaOutputCapture

    with ScriptExecutionCapture(tee=True) as py, MayaOutputCapture() as mx:
        exec(code, globals_)
    merged_stdout = py.stdout + mx.stdout
    merged_stderr = py.stderr + mx.stderr

See: https://github.com/loonghao/dcc-mcp-maya/issues/151
"""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging
from typing import Any, List, Optional

__all__ = ["MayaOutputCapture"]

_LOG = logging.getLogger(__name__)

# MCommandMessage output-type constants (mirror the OpenMaya enum values
# so we can classify messages without keeping a live import around).
# Values are stable across supported Maya versions.
_MSG_TYPE_INFO = 1  # kInfo
_MSG_TYPE_WARNING = 2  # kWarning
_MSG_TYPE_ERROR = 3  # kError
_MSG_TYPE_RESULT = 4  # kResult
_MSG_TYPE_STACK_TRACE = 5  # kStackTrace


def _load_openmaya() -> Optional[Any]:
    """Return the most appropriate ``OpenMaya`` module, or ``None``.

    Prefers the modern API (``maya.api.OpenMaya``), falls back to the
    legacy API if only that is available.  Returns ``None`` when neither
    can be imported so callers can degrade gracefully.
    """
    try:
        from maya.api import OpenMaya as _om  # noqa: PLC0415

        return _om
    except Exception:  # noqa: BLE001 — any import-time failure should degrade
        pass
    try:
        from maya import OpenMaya as _om_legacy  # noqa: PLC0415

        return _om_legacy
    except Exception:  # noqa: BLE001
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
        ``kStackTrace``.  Warnings and errors are grouped here so MCP
        clients can surface them in a failure panel.

    The capture is a **best-effort** helper: if Maya's Python API is not
    importable, both attributes remain empty strings and entering /
    exiting the context is a no-op.  This keeps unit tests that run
    without a live Maya session from needing any special mocking.
    """

    def __init__(self) -> None:
        self._om: Optional[Any] = None
        self._callback_id: Optional[Any] = None
        self._stdout_buf: List[str] = []
        self._stderr_buf: List[str] = []

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

        Signature matches both the modern ``maya.api.OpenMaya`` and the
        legacy ``maya.OpenMaya`` calling conventions — the legacy API
        passes a ``client_data`` argument that the modern API omits, so
        we default it to ``None`` and ignore it.
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
