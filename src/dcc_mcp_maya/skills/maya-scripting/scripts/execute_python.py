"""Execute Python code inside Maya's interpreter.

Supports two execution modes:

* **Inline (default)** — ``exec()`` runs synchronously on the calling
  thread.  ``maya.cmds`` output is captured via both
  :class:`~dcc_mcp_core.script_execution.ScriptExecutionCapture` and
  :class:`~dcc_mcp_maya._maya_output.MayaOutputCapture` so ``print()``,
  ``cmds.warning(...)``, ``cmds.error(...)`` and MEL ``print`` all reach
  the MCP client (issue #151).

* **Deferred (``defer=True``)** — the snippet is scheduled via
  ``maya.utils.executeDeferred`` and a
  :class:`~dcc_mcp_core._server.DeferredToolResult` is returned so the
  MCP request thread is freed immediately (issue #153).  A cooperative
  ``sys.settrace`` interrupt checks the request-level cancellation token
  between Python lines so long-running pure-Python loops can be aborted
  when a client sends ``notifications/cancelled`` — no manual
  :func:`check_maya_cancelled` call required.  Blocking C++ calls
  (``cmds.file(open=...)``, ``cmds.render``, simulations) cannot be
  preempted and will finish the current step before the cancel is
  observed; callers should place
  :func:`dcc_mcp_maya.check_maya_cancelled` inside their own loops for
  finer control.
"""

# Import future modules
from __future__ import annotations

# Import built-in modules
import sys
import threading
import time
from typing import Any, Dict, Optional

# Import local modules
from dcc_mcp_core.skill import skill_entry, skill_error, skill_exception, skill_success

DEFAULT_EXECUTE_TIMEOUT_SECS = 60.0


class ToolTimeoutError(TimeoutError):
    """Raised when execute_python exceeds its cooperative timeout."""

    def __init__(self, elapsed_secs: float) -> None:
        super().__init__("execute_python timed out after {:.3f}s".format(elapsed_secs))
        self.elapsed_secs = elapsed_secs


def _normalize(params: Dict[str, Any]):
    """Normalize ``code``/``script``/``source`` and ``timeout``/``timeout_secs``.

    Wraps :func:`dcc_mcp_core.normalize_script_execution_params` so a
    missing source returns a structured :func:`skill_error` instead of a
    ``ValueError`` propagating up to the dispatcher.
    """
    from dcc_mcp_core.script_execution import normalize_script_execution_params  # noqa: PLC0415

    try:
        return normalize_script_execution_params(params), None
    except ValueError as exc:
        return None, skill_error(
            "No Python code provided",
            str(exc),
            possible_solutions=[
                "Pass the source via the 'code' parameter.",
            ],
        )
    except TypeError as exc:
        return None, skill_error("Invalid script parameter", str(exc))


def _merge_capture(primary: str, extra: str) -> str:
    """Concatenate two capture buffers, preserving blank-line separation."""
    if not extra:
        return primary
    if not primary:
        return extra
    if primary.endswith("\n"):
        return primary + extra
    return primary + "\n" + extra


def _run_inline(
    code: str,
    capture_output: bool,
    cancel_event: Optional[threading.Event] = None,
    timeout_secs: Optional[float] = None,
) -> dict:
    """Run *code* synchronously and return the structured envelope.

    Uses :class:`dcc_mcp_core.script_execution.ScriptExecutionCapture`
    plus :class:`dcc_mcp_maya._maya_output.MayaOutputCapture` (issue
    #151) so ``print()``, ``cmds.warning(...)`` and MEL ``print``
    statements all reach the client while the artist still sees output
    in the Script Editor.

    When *cancel_event* is provided a lightweight :func:`sys.settrace`
    hook checks it between Python lines and raises
    :class:`~dcc_mcp_core.cancellation.CancelledError` when set — this
    is the cooperative preemption used by the deferred path (issue
    #153).
    """
    from dcc_mcp_core.script_execution import ScriptExecutionCapture  # noqa: PLC0415

    # Import local modules
    from dcc_mcp_maya._maya_output import MayaOutputCapture  # noqa: PLC0415

    try:
        import maya.cmds as cmds  # noqa: PLC0415
    except ImportError:
        cmds = None  # type: ignore[assignment]

    exec_globals: Dict[str, Any] = {"cmds": cmds, "__name__": "__maya_exec__"}
    py_capture = ScriptExecutionCapture(tee=True) if capture_output else None
    maya_capture = MayaOutputCapture() if capture_output else None

    # Optional cooperative cancel tracer (deferred path only).  Guarded
    # so the sync path does not pay the ``sys.settrace`` cost.
    trace_installed = False
    previous_trace = None
    started_at = time.monotonic()
    deadline = started_at + timeout_secs if timeout_secs and timeout_secs > 0 else None

    def _cancel_tracer(_frame: Any, event: str, _arg: Any):
        if event == "line":
            if deadline is not None and time.monotonic() >= deadline:
                raise ToolTimeoutError(time.monotonic() - started_at)
            if cancel_event is not None and cancel_event.is_set():
                from dcc_mcp_core.cancellation import CancelledError  # noqa: PLC0415

                raise CancelledError("execute_python cancelled by client")
        return _cancel_tracer

    try:
        if py_capture is not None:
            py_capture.__enter__()
        if maya_capture is not None:
            maya_capture.__enter__()

        if cancel_event is not None or deadline is not None:
            previous_trace = sys.gettrace()
            sys.settrace(_cancel_tracer)
            trace_installed = True

        exc_info: Optional[BaseException] = None
        try:
            exec(compile(code, "<maya-python>", "exec"), exec_globals)  # noqa: S102
        except BaseException as exc:  # noqa: BLE001 — relay traceback to client
            exc_info = exc
    finally:
        if trace_installed:
            sys.settrace(previous_trace)
        if maya_capture is not None:
            maya_capture.__exit__(None, None, None)
        if py_capture is not None:
            py_capture.__exit__(None, None, None)

    py_stdout = py_capture.stdout if py_capture is not None else ""
    py_stderr = py_capture.stderr if py_capture is not None else ""
    maya_stdout = maya_capture.stdout if maya_capture is not None else ""
    maya_stderr = maya_capture.stderr if maya_capture is not None else ""
    stdout = _merge_capture(py_stdout, maya_stdout)
    stderr = _merge_capture(py_stderr, maya_stderr)

    if exc_info is not None:
        if isinstance(exc_info, ToolTimeoutError):
            return skill_error(
                "Python execution timed out",
                str(exc_info),
                kind="tool-timeout",
                elapsed_secs=exc_info.elapsed_secs,
                stdout=stdout,
                stderr=stderr,
            )
        try:
            from dcc_mcp_maya.api import classify_maya_exception  # noqa: PLC0415

            error_code = classify_maya_exception(exc_info)
        except Exception:  # noqa: BLE001
            error_code = "UNKNOWN"
        result = skill_exception(
            exc_info,
            message="Python execution failed",
            stdout=stdout,
            stderr=stderr,
            error_code=error_code,
            error_type=type(exc_info).__name__,
        )
        result.setdefault("error_code", error_code)
        result.setdefault("error_type", type(exc_info).__name__)
        return result

    raw = exec_globals.get("result")
    return skill_success(
        "Python executed successfully",
        prompt="Python script finished. Check 'output' for any return value.",
        output=str(raw) if raw is not None else "",
        stdout=stdout,
        stderr=stderr,
    )


def _run_deferred(code: str, capture_output: bool, timeout_secs: float):
    """Schedule *code* on Maya's idle queue and return a DeferredToolResult.

    The MCP request returns immediately; the dispatcher polls
    :attr:`DeferredToolResult.check_is_finished` until the script
    completes (or ``timeout_secs`` elapses).

    Cancellation (issue #153)
    -------------------------
    Two cooperative hooks keep the deferred job aligned with MCP
    ``notifications/cancelled``:

    1. The polling callback calls
       :func:`~dcc_mcp_maya.check_maya_cancelled` on every invocation.
       When cancelled, it sets ``cancel_event`` (so the worker can
       notice) and re-raises :class:`CancelledError` — the core poll
       loop then returns an error envelope to the client immediately,
       freeing the request thread instead of waiting for the background
       job to finish.
    2. The worker runs under a :func:`sys.settrace` hook that checks
       ``cancel_event`` between Python lines, raising
       :class:`CancelledError` so pure-Python loops abort without the
       caller having to embed manual ``check_maya_cancelled()`` calls.
    """
    from dcc_mcp_core._server import DeferredToolResult  # noqa: PLC0415

    # Import local modules
    from dcc_mcp_maya.dispatcher import check_maya_cancelled  # noqa: PLC0415

    cancel_event = threading.Event()
    state: Dict[str, Any] = {"done": False, "result": None}

    def _runner() -> None:
        state["result"] = _run_inline(code, capture_output, cancel_event=cancel_event, timeout_secs=timeout_secs)
        state["done"] = True

    try:
        import maya.cmds as cmds  # noqa: PLC0415
        import maya.utils  # noqa: PLC0415

        if cmds.about(batch=True):
            _runner()
        else:
            maya.utils.executeDeferred(_runner)
    except ImportError:
        # mayapy / standalone — no executeDeferred queue; run inline.
        _runner()

    def _check_is_finished():
        # Propagate MCP cancellation to the worker + the core poll loop.
        try:
            check_maya_cancelled()
        except BaseException:  # noqa: BLE001 — flag worker + re-raise
            cancel_event.set()
            raise
        return state["result"] if state["done"] else None

    return DeferredToolResult(
        check_is_finished=_check_is_finished,
        timeout_secs=float(timeout_secs),
        poll_interval_secs=0.1,
    )


def execute_python(**params: Any):
    """Execute a Python snippet with ``maya.cmds`` pre-imported.

    Accepts the source via ``code`` (preferred), ``script``, or ``source``
    (issue #150 / dcc-mcp-core #591).  When ``capture_output=True``
    (default) ``print()``, ``cmds.warning(...)`` and MEL ``print`` output
    are all captured (issue #151).  When ``defer=True`` the script is
    scheduled on Maya's idle queue and a :class:`DeferredToolResult` is
    returned so long-running scripts no longer block the MCP request
    thread, with cooperative cancellation wired in (issue #153).
    """
    normalized, err = _normalize(params)
    if err is not None:
        return err

    code = normalized.code  # type: ignore[union-attr]
    if not code.strip():
        return skill_error("No Python code provided", "Provide non-empty source.")

    capture_output = bool(params.get("capture_output", True))
    defer = bool(params.get("defer", False))
    timeout_secs = normalized.timeout_secs  # type: ignore[union-attr]

    effective_timeout = float(timeout_secs or DEFAULT_EXECUTE_TIMEOUT_SECS)
    if defer:
        return _run_deferred(code, capture_output, effective_timeout)
    return _run_inline(code, capture_output, timeout_secs=effective_timeout)


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`execute_python`."""
    return execute_python(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
