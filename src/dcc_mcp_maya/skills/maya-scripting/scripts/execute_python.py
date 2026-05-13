"""Execute Python code inside Maya's interpreter.

Supports three execution shapes:

* **Inline (default)** — ``exec()`` runs synchronously on the calling
  thread with an isolated namespace (``maya.cmds`` pre-imported).  Output
  is captured via both
  :class:`~dcc_mcp_core.script_execution.ScriptExecutionCapture` and
  :class:`~dcc_mcp_maya._maya_output.MayaOutputCapture` so ``print()``,
  ``cmds.warning(...)``, ``cmds.error(...)`` and MEL ``print`` all reach
  the MCP client (issue #151).  Very long inline ``code`` strings are
  mirrored to a host-local temp file before ``exec`` (see
  ``context.host_spilled_inline_script_path``); prefer explicit
  ``file_path`` or typed skills when possible.

* **File (``file_path`` / ``script_path``)** — reads a ``.py`` file and
  runs it in ``__import__('__main__').__dict__`` with ``__file__`` and
  ``this_root`` set, matching typical Maya shelf / pipeline script
  expectations. The path must be readable **inside this Maya process**
  (not only on a remote agent host talking to the gateway).

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
import os
import sys
import threading
import time
from collections.abc import Mapping
from typing import Any, Dict, Optional

# Import local modules
from dcc_mcp_core.skill import skill_entry, skill_error, skill_exception, skill_success

DEFAULT_EXECUTE_TIMEOUT_SECS = 60.0

# Inline ``code`` longer than this is copied to a host-local file (see
# :func:`dcc_mcp_core.script_execution.write_temp_script`) before ``exec`` so
# large gateway payloads and JSON escaping issues align with the file-backed
# execution path. Typed skills remain preferred over long inline scripts.
INLINE_CODE_SPILL_THRESHOLD_CHARS = 4096


def _persist_inline_spill_to_host_temp(code: str) -> str:
    """Write *code* to ``~/.dcc-mcp-core/temp_scripts/`` and return the path.

    Prefer :func:`dcc_mcp_core.script_execution.write_temp_script` when the
    installed ``dcc-mcp-core`` wheel exposes it; this fallback keeps Maya
    adapters functional on slightly older core builds.
    """
    import tempfile
    from pathlib import Path

    root_dir = Path.home() / ".dcc-mcp-core" / "temp_scripts"
    root_dir.mkdir(parents=True, exist_ok=True)
    fd, path = tempfile.mkstemp(suffix=".py", prefix="dcc_mcp_", dir=str(root_dir))
    with os.fdopen(fd, "w", encoding="utf-8") as fp:
        fp.write(code)
    return path


try:
    from dcc_mcp_core.script_execution import write_temp_script as _write_inline_spill_file
except ImportError:  # pragma: no cover — older dcc-mcp-core without write_temp_script
    _write_inline_spill_file = _persist_inline_spill_to_host_temp


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
                "Or pass file_path (or script_path) to a .py file for native __main__ execution.",
            ],
        )
    except TypeError as exc:
        return None, skill_error("Invalid script parameter", str(exc))


def _merge_capture(primary: str, extra: str) -> str:
    """Concatenate capture buffers while dropping Maya's mirrored stdout."""
    if not extra:
        return primary
    if not primary:
        return extra
    primary_lines = [line.strip() for line in primary.splitlines() if line.strip()]
    extra_lines = [line.strip() for line in extra.splitlines() if line.strip()]
    if extra_lines and all(line in primary_lines for line in extra_lines):
        return primary
    if extra_lines and " ".join(extra_lines) in primary_lines:
        return primary
    if primary.endswith("\n"):
        return primary + extra
    return primary + "\n" + extra


def _attach_spill_context(result: Dict[str, Any], spilled_path: Optional[str]) -> Dict[str, Any]:
    """Annotate success envelopes when inline code was mirrored to disk on the Maya host."""
    if not spilled_path or not result.get("success"):
        return result
    ctx = result.get("context")
    if not isinstance(ctx, dict):
        return result
    if ctx.get("host_spilled_inline_script_path"):
        return result
    ctx["host_spilled_inline_script_path"] = spilled_path
    ctx["host_spill_reason"] = "inline_code_exceeded_threshold_chars"
    return result


def _resolve_script_file_path(params: Mapping[str, Any]) -> Optional[str]:
    """Return the first non-empty ``file_path`` / ``script_path`` string, if any."""
    for key in ("file_path", "script_path"):
        raw = params.get(key)
        if raw is None:
            continue
        s = str(raw).strip()
        if s:
            return s
    return None


def _parse_timeout_secs_param(params: Dict[str, Any]) -> Optional[float]:
    """Parse ``timeout_secs`` from raw tool params (not via normalize_script_execution_params)."""
    v = params.get("timeout_secs")
    if v is None or isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        f = float(v)
        return f if f > 0 else None
    return None


def _run_inline_impl(
    code: str,
    filename: str,
    exec_globals: Dict[str, Any],
    capture_output: bool,
    cancel_event: Optional[threading.Event] = None,
    timeout_secs: Optional[float] = None,
) -> dict:
    """Shared exec + capture path for inline and file-backed execution."""
    from dcc_mcp_core.script_execution import ScriptExecutionCapture  # noqa: PLC0415

    # Import local modules
    from dcc_mcp_maya._maya_output import MayaOutputCapture  # noqa: PLC0415

    py_capture = ScriptExecutionCapture(tee=True) if capture_output else None
    maya_capture = MayaOutputCapture() if capture_output else None

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

    exc_info: Optional[BaseException] = None
    cleanup_error: Optional[BaseException] = None
    try:
        if py_capture is not None:
            py_capture.__enter__()
        if maya_capture is not None:
            maya_capture.__enter__()

        if cancel_event is not None or deadline is not None:
            previous_trace = sys.gettrace()
            sys.settrace(_cancel_tracer)
            trace_installed = True

        try:
            exec(compile(code, filename, "exec"), exec_globals)  # noqa: S102
        except BaseException as exc:  # noqa: BLE001 — relay traceback to client
            exc_info = exc
    finally:
        if trace_installed:
            sys.settrace(previous_trace)
        for capture in (maya_capture, py_capture):
            if capture is None:
                continue
            try:
                capture.__exit__(None, None, None)
            except BaseException as exc:  # noqa: BLE001
                if cleanup_error is None:
                    cleanup_error = exc
        if exc_info is None and cleanup_error is not None:
            exc_info = cleanup_error

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
            from dcc_mcp_maya.api import (  # noqa: PLC0415
                canonical_maya_exception_message,
                classify_maya_exception,
            )

            error_code = classify_maya_exception(exc_info)
            canonical_message = canonical_maya_exception_message(exc_info)
        except Exception:  # noqa: BLE001
            error_code = "UNKNOWN"
            canonical_message = "Unknown Maya error."
        result = skill_exception(
            exc_info,
            message="Python execution failed",
            stdout=stdout,
            stderr=stderr,
            error_code=error_code,
            canonical_message_en=canonical_message,
            error_type=type(exc_info).__name__,
        )
        result.setdefault("error_code", error_code)
        result.setdefault("canonical_message_en", canonical_message)
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


def _run_inline(
    code: str,
    capture_output: bool,
    cancel_event: Optional[threading.Event] = None,
    timeout_secs: Optional[float] = None,
    *,
    exec_filename: str = "<maya-python>",
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

    *exec_filename* is passed to :func:`compile` for stack traces (may be a
    host temp path when inline code was spilled to disk).
    """
    try:
        import maya.cmds as cmds  # noqa: PLC0415
    except ImportError:
        cmds = None  # type: ignore[assignment]

    exec_globals: Dict[str, Any] = {"cmds": cmds, "__name__": "__maya_exec__"}
    return _run_inline_impl(
        code,
        exec_filename,
        exec_globals,
        capture_output,
        cancel_event=cancel_event,
        timeout_secs=timeout_secs,
    )


def _run_inline_file_path(
    file_path: str,
    capture_output: bool,
    cancel_event: Optional[threading.Event] = None,
    timeout_secs: Optional[float] = None,
) -> dict:
    """Run a ``.py`` file like Maya's Script Editor: ``__main__`` globals + ``__file__``."""
    expanded = os.path.abspath(os.path.expanduser(str(file_path).strip()))
    if not os.path.isfile(expanded):
        return skill_error(
            "Script file not found",
            expanded,
            possible_solutions=["Check file_path is readable from the Maya process."],
        )
    if not expanded.lower().endswith(".py"):
        return skill_error(
            "file_path must be a .py file",
            expanded,
            possible_solutions=["Use execute_mel with file_path for .mel scripts."],
        )
    try:
        with open(expanded, encoding="utf-8", errors="replace") as fh:
            body = fh.read()
    except OSError as exc:
        return skill_error("Could not read script file", str(exc), path=expanded)

    ns = __import__("__main__").__dict__
    ns["this_root"] = os.path.dirname(expanded)
    ns["__file__"] = expanded
    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if "cmds" not in ns or ns.get("cmds") is None:
            ns["cmds"] = cmds
    except ImportError:
        if "cmds" not in ns:
            ns["cmds"] = None

    return _run_inline_impl(
        body,
        expanded,
        ns,
        capture_output,
        cancel_event=cancel_event,
        timeout_secs=timeout_secs,
    )


def _run_deferred(
    code: str,
    capture_output: bool,
    timeout_secs: float,
    *,
    exec_filename: str = "<maya-python>",
    spilled_path: Optional[str] = None,
):
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
        envelope = _run_inline(
            code,
            capture_output,
            cancel_event=cancel_event,
            timeout_secs=timeout_secs,
            exec_filename=exec_filename,
        )
        state["result"] = _attach_spill_context(envelope, spilled_path)
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


def _run_deferred_file(file_path: str, capture_output: bool, timeout_secs: float):
    """Like :func:`_run_deferred` but runs :func:`_run_inline_file_path` on the worker."""
    from dcc_mcp_core._server import DeferredToolResult  # noqa: PLC0415

    from dcc_mcp_maya.dispatcher import check_maya_cancelled  # noqa: PLC0415

    cancel_event = threading.Event()
    state: Dict[str, Any] = {"done": False, "result": None}

    def _runner() -> None:
        state["result"] = _run_inline_file_path(
            file_path,
            capture_output,
            cancel_event=cancel_event,
            timeout_secs=timeout_secs,
        )
        state["done"] = True

    try:
        import maya.cmds as cmds  # noqa: PLC0415
        import maya.utils  # noqa: PLC0415

        if cmds.about(batch=True):
            _runner()
        else:
            maya.utils.executeDeferred(_runner)
    except ImportError:
        _runner()

    def _check_is_finished():
        try:
            check_maya_cancelled()
        except BaseException:  # noqa: BLE001
            cancel_event.set()
            raise
        return state["result"] if state["done"] else None

    return DeferredToolResult(
        check_is_finished=_check_is_finished,
        timeout_secs=float(timeout_secs),
        poll_interval_secs=0.1,
    )


def execute_python(**params: Any):
    """Execute a Python snippet or a ``.py`` file inside Maya.

    Inline source uses an isolated namespace with ``maya.cmds`` pre-imported.
    When ``file_path`` (or ``script_path``) is set, the file is run like Maya's
    Script Editor: ``exec`` uses ``__import__('__main__').__dict__`` with
    ``__file__`` and ``this_root`` populated (studio shelf / pipeline scripts).

    Accepts inline source via ``code`` (preferred), ``script``, or ``source``
    (issue #150 / dcc-mcp-core #591).  When ``capture_output=True``
    (default) ``print()``, ``cmds.warning(...)`` and MEL ``print`` output
    are all captured (issue #151).  When ``defer=True`` the script is
    scheduled on Maya's idle queue and a :class:`DeferredToolResult` is
    returned so long-running scripts no longer block the MCP request
    thread, with cooperative cancellation wired in (issue #153).
    """
    from dcc_mcp_maya._env import (  # noqa: PLC0415
        ENV_DISABLE_ARBITRARY_SCRIPT,
        ENV_DISABLE_EXECUTE_PYTHON,
        resolve_execute_python_disabled,
    )

    if resolve_execute_python_disabled():
        return skill_error(
            "execute_python is disabled by operator policy",
            "Unset {} or {} to re-enable arbitrary Python execution.".format(
                ENV_DISABLE_EXECUTE_PYTHON,
                ENV_DISABLE_ARBITRARY_SCRIPT,
            ),
            possible_solutions=[
                "Use search_skills(query=...) → load_skill('<skill>') → call the typed tool "
                "from that skill's tools.yaml (validated inputSchema).",
                "Use dcc_capability_manifest with {loaded_only: false} to pick a skill without inflating tools/list.",
                "Gateway / non-MCP clients: POST http://<gateway>:<port>/v1/search, /v1/describe, "
                "/v1/call (or /v1/call_batch) — do not assume the per-Maya /mcp URL is the only surface.",
                "MCP-only hosts: search_tools → describe_tool → call_tool on the bounded slug surface.",
                "Use introspect_* tools in maya-scripting when you only need API discovery.",
            ],
        )

    capture_output = bool(params.get("capture_output", True))
    defer = bool(params.get("defer", False))

    file_arg = _resolve_script_file_path(params)
    if file_arg is not None:
        from_file_timeout = _parse_timeout_secs_param(params)
        effective_timeout = float(from_file_timeout or DEFAULT_EXECUTE_TIMEOUT_SECS)
        if defer:
            return _run_deferred_file(file_arg, capture_output, effective_timeout)
        return _run_inline_file_path(file_arg, capture_output, timeout_secs=effective_timeout)

    normalized, err = _normalize(params)
    if err is not None:
        return err

    code = normalized.code  # type: ignore[union-attr]
    if not code.strip():
        return skill_error("No Python code provided", "Provide non-empty source.")

    timeout_secs = normalized.timeout_secs  # type: ignore[union-attr]

    effective_timeout = float(timeout_secs or DEFAULT_EXECUTE_TIMEOUT_SECS)

    exec_filename = "<maya-python>"
    spilled_path: Optional[str] = None
    if len(code) > INLINE_CODE_SPILL_THRESHOLD_CHARS:
        spilled_path = _write_inline_spill_file(code)
        exec_filename = spilled_path

    if defer:
        return _run_deferred(
            code,
            capture_output,
            effective_timeout,
            exec_filename=exec_filename,
            spilled_path=spilled_path,
        )
    envelope = _run_inline(
        code,
        capture_output,
        timeout_secs=effective_timeout,
        exec_filename=exec_filename,
    )
    return _attach_spill_context(envelope, spilled_path)


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`execute_python`."""
    return execute_python(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
