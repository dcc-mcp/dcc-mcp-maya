"""Execute Python code inside Maya's interpreter."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging

logger = logging.getLogger(__name__)


def execute_python(code: str, capture_output: bool = False) -> dict:
    """Execute an arbitrary Python snippet with Maya cmds pre-imported.

    The executed code runs in a namespace that pre-loads ``maya.cmds`` as
    ``cmds``.  If the code assigns to a variable named ``result``, its string
    representation is returned in ``context.output``.  Set
    ``capture_output=True`` to capture ``print()`` output instead.

    Args:
        code: Python source code to execute.
        capture_output: If True, capture stdout via ``io.StringIO``. Default False.

    Returns:
        ActionResultModel dict with ``context.output`` (str) and ``context.stdout``
        (str, only when ``capture_output=True``).
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    if not code or not code.strip():
        return error_result("No Python code provided", "Provide 'code' with valid Python.").to_dict()

    # Import built-in modules
    import io
    import sys

    try:
        import maya.cmds as cmds  # noqa: PLC0415
    except ImportError:
        cmds = None  # type: ignore[assignment]

    exec_globals = {"cmds": cmds}

    try:
        if capture_output:
            old_stdout = sys.stdout
            sys.stdout = io.StringIO()
            try:
                exec(compile(code, "<maya-python>", "exec"), exec_globals)  # noqa: S102
                captured = sys.stdout.getvalue()
            finally:
                sys.stdout = old_stdout
            output = captured
        else:
            exec(compile(code, "<maya-python>", "exec"), exec_globals)  # noqa: S102
            # Expose any 'result' variable the executed code set
            raw = exec_globals.get("result")
            output = str(raw) if raw is not None else ""
            captured = ""

        return success_result(
            "Python executed successfully",
            prompt="Python script finished. Check 'output' for any return value.",
            output=output,
            stdout=captured,
        ).to_dict()
    except Exception as exc:
        logger.exception("execute_python failed")
        return error_result("Python execution failed", str(exc)).to_dict()


def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`execute_python`."""
    return execute_python(**kwargs)


if __name__ == "__main__":
    import json

    result = execute_python("result = 'hello'")
    print(json.dumps(result))
