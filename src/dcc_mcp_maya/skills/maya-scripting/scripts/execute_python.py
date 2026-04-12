"""Execute Python code inside Maya's interpreter."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import time

# Import local modules
from dcc_mcp_core.skill import skill_entry, skill_error, skill_exception, skill_success
from dcc_mcp_maya.api import make_input_validator, validate_input

# Pre-built validator: 'code' is a required non-empty string (max 1MB)
_VALIDATOR = make_input_validator(
    string_fields={"code": (1, 1_000_000)},
)

# Dangerous patterns that indicate code injection attempts
_DANGEROUS_PATTERNS = [
    "os.system",
    "subprocess",
    "__import__",
    "eval(",
    "exec(",
    "importlib",
    "open(",
    "shutil.rmtree",
    "os.remove",
    "os.unlink",
    "os.rmdir",
]


def _check_injection(code: str):
    """Return an error dict if *code* contains dangerous patterns, else None."""
    for pattern in _DANGEROUS_PATTERNS:
        if pattern in code:
            return skill_error(
                "Potential code injection detected",
                "Code contains forbidden pattern: '{}'".format(pattern),
                possible_solutions=[
                    "Remove dangerous calls from the code",
                    "Use Maya cmds API instead of raw OS/subprocess calls",
                ],
            )
    return None


def execute_python(code: str, capture_output: bool = False) -> dict:
    """Execute an arbitrary Python snippet with Maya cmds pre-imported.

    Validates the ``code`` parameter using ``InputValidator`` and checks for
    dangerous code injection patterns before execution.  Returns structured
    output compatible with ``ScriptResult``.

    The executed code runs in a namespace that pre-loads ``maya.cmds`` as
    ``cmds``.  If the code assigns to a variable named ``result``, its string
    representation is returned in ``context.output``.  Set
    ``capture_output=True`` to capture ``print()`` output instead.

    Args:
        code: Python source code to execute.
        capture_output: If True, capture stdout via ``io.StringIO``. Default False.

    Returns:
        ActionResultModel dict with ``context.output`` (str),
        ``context.stdout`` (str, only when ``capture_output=True``),
        ``context.execution_time_ms`` (float),
        and ``context.script_result`` (ScriptResult-compatible dict).
    """
    ok, err_msg = validate_input(_VALIDATOR, {"code": code})
    if not ok:
        return skill_error(
            "Invalid input",
            err_msg or "code field validation failed",
            possible_solutions=["Provide 'code' with valid Python code"],
        )

    if not code or not code.strip():
        return skill_error("No Python code provided", "Provide 'code' with valid Python.")

    # Injection guard
    injection_err = _check_injection(code)
    if injection_err is not None:
        return injection_err

    # Import built-in modules
    import io
    import sys

    try:
        import maya.cmds as cmds  # noqa: PLC0415
    except ImportError:
        cmds = None  # type: ignore[assignment]

    exec_globals = {"cmds": cmds}

    try:
        t0 = time.time()
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
            raw = exec_globals.get("result")
            output = str(raw) if raw is not None else ""
            captured = ""

        elapsed_ms = (time.time() - t0) * 1000.0

        script_result = {
            "success": True,
            "output": output,
            "error": "",
            "execution_time_ms": elapsed_ms,
            "context": {"code": code, "capture_output": capture_output},
        }
        return skill_success(
            "Python executed successfully",
            prompt="Python script finished. Check 'output' for any return value.",
            output=output,
            stdout=captured,
            execution_time_ms=elapsed_ms,
            script_result=script_result,
        )
    except Exception as exc:
        return skill_exception(exc, message="Python execution failed")


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`execute_python`."""
    return execute_python(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
