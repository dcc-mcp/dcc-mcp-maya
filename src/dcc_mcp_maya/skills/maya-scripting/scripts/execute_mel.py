"""Execute a MEL script inside Maya."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import time

# Import local modules
from dcc_mcp_core.skill import skill_entry, skill_error, skill_exception, skill_success
from dcc_mcp_maya.api import make_input_validator, validate_input

# Pre-built validator: 'script' is a required non-empty string (max 1MB)
_VALIDATOR = make_input_validator(
    string_fields={"script": (1, 1_000_000)},
)


def execute_mel(script: str) -> dict:
    """Execute a MEL expression and return its string result.

    Validates the ``script`` parameter using ``InputValidator`` before
    execution, ensuring the field is present and non-empty.  Returns
    structured output compatible with ``ScriptResult``.

    Args:
        script: MEL code to execute.

    Returns:
        ActionResultModel dict with ``context.output`` (str),
        ``context.script``, ``context.execution_time_ms`` (float),
        and ``context.script_result`` (ScriptResult-compatible dict).
    """
    ok, err_msg = validate_input(_VALIDATOR, {"script": script})
    if not ok:
        return skill_error(
            "Invalid input",
            err_msg or "script field validation failed",
            possible_solutions=["Provide 'script' with valid MEL code"],
        )

    if not script or not script.strip():
        return skill_error("No MEL code provided", "Provide 'script' with valid MEL.")

    try:
        import maya.mel as mel  # noqa: PLC0415

        t0 = time.time()
        raw = mel.eval(script)
        elapsed_ms = (time.time() - t0) * 1000.0
        output = str(raw) if raw is not None else ""

        script_result = {
            "success": True,
            "output": output,
            "error": "",
            "execution_time_ms": elapsed_ms,
            "context": {"script": script},
        }
        return skill_success(
            "MEL executed successfully",
            prompt="MEL script finished. Check 'output' for any return value.",
            output=output,
            script=script,
            execution_time_ms=elapsed_ms,
            script_result=script_result,
        )
    except ImportError:
        return skill_error("Maya not available", "maya.mel could not be imported")
    except Exception as exc:
        return skill_exception(exc, message="MEL execution failed")


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`execute_mel`."""
    return execute_mel(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
