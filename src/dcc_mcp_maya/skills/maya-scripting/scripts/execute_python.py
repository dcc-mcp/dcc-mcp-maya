"""Execute Python code inside Maya's interpreter."""

# Import future modules
from __future__ import annotations

# Import built-in modules
from typing import Any, Dict

# Import local modules
from dcc_mcp_core.skill import skill_entry, skill_error, skill_exception, skill_success


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
                "Pass the source via 'code' (preferred), 'script', or 'source'.",
            ],
        )
    except TypeError as exc:
        return None, skill_error("Invalid script parameter", str(exc))


def _run_inline(code: str, capture_output: bool) -> dict:
    """Run *code* synchronously and return the structured envelope.

    Uses :class:`dcc_mcp_core.script_execution.ScriptExecutionCapture`
    (issue #151) to capture ``print()`` and ``cmds.warning(...)`` output
    while preserving the historical ``context.output`` / ``context.stdout``
    keys so existing MCP clients keep working.
    """
    from dcc_mcp_core.script_execution import ScriptExecutionCapture  # noqa: PLC0415

    try:
        import maya.cmds as cmds  # noqa: PLC0415
    except ImportError:
        cmds = None  # type: ignore[assignment]

    exec_globals: Dict[str, Any] = {"cmds": cmds, "__name__": "__maya_exec__"}
    capture = ScriptExecutionCapture(tee=True) if capture_output else None
    try:
        if capture is not None:
            with capture:
                exec(compile(code, "<maya-python>", "exec"), exec_globals)  # noqa: S102
            stdout, stderr = capture.stdout, capture.stderr
        else:
            exec(compile(code, "<maya-python>", "exec"), exec_globals)  # noqa: S102
            stdout, stderr = "", ""
    except BaseException as exc:  # noqa: BLE001 — relay traceback to client
        captured_out = capture.stdout if capture is not None else ""
        captured_err = capture.stderr if capture is not None else ""
        return skill_exception(
            exc,
            message="Python execution failed",
            stdout=captured_out,
            stderr=captured_err,
        )

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
    completes (or :attr:`timeout_secs` elapses).
    """
    from dcc_mcp_core._server import DeferredToolResult  # noqa: PLC0415

    state: Dict[str, Any] = {"done": False, "result": None}

    def _runner() -> None:
        state["result"] = _run_inline(code, capture_output)
        state["done"] = True

    try:
        import maya.utils  # noqa: PLC0415

        maya.utils.executeDeferred(_runner)
    except ImportError:
        # mayapy / standalone — no executeDeferred queue; run inline.
        _runner()

    return DeferredToolResult(
        check_is_finished=lambda: state["result"] if state["done"] else None,
        timeout_secs=float(timeout_secs),
        poll_interval_secs=0.1,
    )


def execute_python(**params: Any):
    """Execute a Python snippet with ``maya.cmds`` pre-imported.

    Accepts the source via ``code`` (preferred), ``script``, or ``source``
    (issue #150 / dcc-mcp-core #591).  When ``capture_output=True``
    (default) ``print()`` and ``cmds.warning(...)`` output are captured
    via :class:`ScriptExecutionCapture` (issue #151).  When ``defer=True``
    the script is scheduled on Maya's idle queue and a
    :class:`DeferredToolResult` is returned so long-running scripts no
    longer block the MCP request thread (issue #153).
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

    if defer:
        return _run_deferred(code, capture_output, float(timeout_secs or 3600))
    return _run_inline(code, capture_output)


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`execute_python`."""
    return execute_python(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
