"""Execute a MEL script inside Maya."""

# Import future modules
from __future__ import annotations

# Import built-in modules
from typing import Any, Dict

# Import local modules
from dcc_mcp_core.skill import skill_entry, skill_error, skill_exception, skill_success


def execute_mel(**params: Any) -> dict:
    """Execute a MEL expression and return its string result.

    Accepts the source via ``code`` (preferred), ``script``, or ``source``
    aliases via :func:`dcc_mcp_core.normalize_script_execution_params` so
    ``execute_mel`` and ``execute_python`` share a common parameter
    contract (issue #150 / dcc-mcp-core #591).  Captured stdout/stderr
    are returned in the structured envelope (issue #151).

    Returns:
        ToolResult dict with ``context.result`` (MEL return value),
        ``context.stdout`` and ``context.stderr``.
    """
    from dcc_mcp_core.script_execution import (  # noqa: PLC0415
        ScriptExecutionCapture,
        normalize_script_execution_params,
    )

    try:
        normalized = normalize_script_execution_params(params)
    except ValueError as exc:
        return skill_error(
            "No MEL code provided",
            str(exc),
            possible_solutions=[
                "Pass the source via 'code' (preferred), 'script', or 'source'.",
            ],
        )
    except TypeError as exc:
        return skill_error("Invalid script parameter", str(exc))

    code = normalized.code
    if not code.strip():
        return skill_error("No MEL code provided", "Provide non-empty source.")

    try:
        import maya.mel as mel  # noqa: PLC0415
    except ImportError:
        return skill_error("Maya not available", "maya.mel could not be imported")

    capture = ScriptExecutionCapture(tee=True)
    try:
        with capture:
            raw = mel.eval(code)
        return skill_success(
            "MEL executed successfully",
            prompt="MEL script finished. Check 'output' for any return value.",
            output=str(raw) if raw is not None else "",
            stdout=capture.stdout,
            stderr=capture.stderr,
            script=code,
        )
    except BaseException as exc:  # noqa: BLE001 — relay traceback to client
        return skill_exception(
            exc,
            message="MEL execution failed",
            stdout=capture.stdout,
            stderr=capture.stderr,
        )


@skill_entry
def main(**kwargs: Any) -> Dict[str, Any]:
    """Entry point; delegates to :func:`execute_mel`."""
    return execute_mel(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
