"""Execute a MEL script inside Maya (inline ``code`` or ``file_path`` / ``script_path``)."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import os
import re
import warnings
from typing import Any, Dict, Optional

# Import local modules
from dcc_mcp_core.skill import skill_entry, skill_error, skill_exception, skill_success

_SCRIPT_PATH_DEPRECATION = "`script_path` is deprecated, use `file_path` instead."


def _resolve_script_file_path(params: Dict[str, Any]) -> Optional[str]:
    file_path = params.get("file_path")
    if file_path is not None:
        cleaned = str(file_path).strip()
        if cleaned:
            return cleaned
    # ``script_path`` is the deprecated alias kept for one release while
    # callers migrate to ``file_path`` (issue #311). It only resolves when
    # ``file_path`` is empty, and emits a ``DeprecationWarning`` so external
    # MCP clients still sending it get a clear migration signal before the
    # alias is dropped here and in the dcc-mcp-core wire schema.
    script_path = params.get("script_path")
    if script_path is not None:
        cleaned = str(script_path).strip()
        if cleaned:
            warnings.warn(_SCRIPT_PATH_DEPRECATION, DeprecationWarning, stacklevel=2)
            return cleaned
    return None


def _mel_source_statement(path: str) -> str:
    """Build a MEL ``source`` argument with forward slashes (Maya-friendly)."""
    norm = os.path.abspath(os.path.expanduser(path)).replace("\\", "/")
    if '"' in norm:
        norm = norm.replace('"', '\\"')
    return 'source "{}"'.format(norm)


_PYTHON_SMOKE_RE = re.compile(r"^[\d\s+\-*/().]+;\s*$")


def _looks_like_python_source(code: str) -> bool:
    """Heuristic: inline source is almost certainly Python, not MEL."""
    stripped = code.strip()
    if not stripped:
        return False
    if stripped.startswith("from ") or " import " in stripped:
        return True
    if stripped.startswith(("def ", "class ", "async def ", "@")):
        return True
    if _PYTHON_SMOKE_RE.match(stripped):
        return True
    return False


def _merge_capture(primary: str, extra: str) -> str:
    """Concatenate two capture buffers, preserving blank-line separation."""
    if not extra:
        return primary
    if not primary:
        return extra
    if primary.endswith("\n"):
        return primary + extra
    return primary + "\n" + extra


def execute_mel(**params: Any) -> dict:
    """Execute a MEL expression and return its string result.

    Accepts the source via the ``code`` parameter, normalised through
    :func:`dcc_mcp_core.normalize_script_execution_params` so ``execute_mel``
    and ``execute_python`` share a common parameter contract (issue #150 /
    dcc-mcp-core #591).

    Captures both Python stdout/stderr **and** Maya's native Script
    Editor channel (``MCommandMessage``) so MEL ``print`` and
    ``warning`` statements are visible to MCP clients (issue #151).

    Returns:
        ToolResult dict with ``context.result`` (MEL return value),
        ``context.stdout`` and ``context.stderr``.
    """
    from dcc_mcp_maya._env import (  # noqa: PLC0415
        ENV_DISABLE_ARBITRARY_SCRIPT,
        ENV_DISABLE_EXECUTE_MEL,
        resolve_execute_mel_disabled,
    )

    if resolve_execute_mel_disabled():
        return skill_error(
            "execute_mel is disabled by operator policy",
            "Unset {} or {} to re-enable arbitrary MEL execution.".format(
                ENV_DISABLE_EXECUTE_MEL,
                ENV_DISABLE_ARBITRARY_SCRIPT,
            ),
            possible_solutions=[
                "Prefer load_skill + typed Python tools over raw MEL when a skill exists.",
                "Use list_mel_procedures or domain skills that wrap the MEL you need.",
                "Gateway / REST clients: POST /v1/call (or /v1/call_batch) on the gateway port — "
                "not only the per-Maya /mcp Streamable HTTP URL.",
            ],
        )

    file_arg = _resolve_script_file_path(params)
    if file_arg is not None:
        expanded = os.path.abspath(os.path.expanduser(file_arg))
        if not os.path.isfile(expanded):
            return skill_error(
                "MEL script file not found",
                expanded,
                possible_solutions=["Verify file_path is visible to the Maya process."],
            )
        if not expanded.lower().endswith(".mel"):
            return skill_error(
                "file_path must be a .mel file",
                expanded,
                possible_solutions=["Pass inline MEL via the code parameter instead."],
            )
        try:
            import maya.mel as mel  # noqa: PLC0415
        except ImportError:
            return skill_error("Maya not available", "maya.mel could not be imported")

        from dcc_mcp_core.script_execution import ScriptExecutionCapture  # noqa: PLC0415

        from dcc_mcp_maya._maya_output import MayaOutputCapture  # noqa: PLC0415

        py_capture = ScriptExecutionCapture(tee=True)
        maya_capture = MayaOutputCapture()
        try:
            with py_capture, maya_capture:
                raw = mel.eval(_mel_source_statement(expanded))
        except BaseException as exc:  # noqa: BLE001
            stdout = _merge_capture(py_capture.stdout, maya_capture.stdout)
            stderr = _merge_capture(py_capture.stderr, maya_capture.stderr)
            return skill_exception(
                exc,
                message="MEL source failed",
                stdout=stdout,
                stderr=stderr,
            )
        stdout = _merge_capture(py_capture.stdout, maya_capture.stdout)
        stderr = _merge_capture(py_capture.stderr, maya_capture.stderr)
        return skill_success(
            "MEL sourced successfully",
            prompt="MEL script finished. Check 'output' for any return value.",
            output=str(raw) if raw is not None else "",
            stdout=stdout,
            stderr=stderr,
            file_path=expanded,
        )

    from dcc_mcp_core.script_execution import (  # noqa: PLC0415
        ScriptExecutionCapture,
        normalize_script_execution_params,
    )

    # Import local modules
    from dcc_mcp_maya._maya_output import MayaOutputCapture  # noqa: PLC0415

    try:
        normalized = normalize_script_execution_params(params)
    except ValueError as exc:
        return skill_error(
            "No MEL code provided",
            str(exc),
            possible_solutions=[
                "Pass the source via the 'code' parameter.",
                "Or pass file_path (or script_path) to a .mel file for MEL `source`.",
            ],
        )
    except TypeError as exc:
        return skill_error("Invalid script parameter", str(exc))

    code = normalized.code
    if not code.strip():
        return skill_error("No MEL code provided", "Provide non-empty source.")

    if _looks_like_python_source(code):
        return skill_error(
            "Source looks like Python, not MEL",
            code.strip()[:200],
            possible_solutions=[
                "Use maya_scripting__execute_python (or gateway call → execute_python) for Python.",
                "MEL does not accept Python smoke tests such as `1+1;` — that pattern belongs in execute_python.",
            ],
        )

    try:
        import maya.mel as mel  # noqa: PLC0415
    except ImportError:
        return skill_error("Maya not available", "maya.mel could not be imported")

    py_capture = ScriptExecutionCapture(tee=True)
    maya_capture = MayaOutputCapture()
    try:
        with py_capture, maya_capture:
            raw = mel.eval(code)
    except BaseException as exc:  # noqa: BLE001 — relay traceback to client
        stdout = _merge_capture(py_capture.stdout, maya_capture.stdout)
        stderr = _merge_capture(py_capture.stderr, maya_capture.stderr)
        return skill_exception(
            exc,
            message="MEL execution failed",
            stdout=stdout,
            stderr=stderr,
        )

    stdout = _merge_capture(py_capture.stdout, maya_capture.stdout)
    stderr = _merge_capture(py_capture.stderr, maya_capture.stderr)
    return skill_success(
        "MEL executed successfully",
        prompt="MEL script finished. Check 'output' for any return value.",
        output=str(raw) if raw is not None else "",
        stdout=stdout,
        stderr=stderr,
        script=code,
    )


@skill_entry
def main(**kwargs: Any) -> Dict[str, Any]:
    """Entry point; delegates to :func:`execute_mel`."""
    return execute_mel(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
