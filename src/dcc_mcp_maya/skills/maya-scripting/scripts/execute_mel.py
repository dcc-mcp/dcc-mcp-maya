"""Execute a MEL script inside Maya."""

# Import future modules
from __future__ import annotations

# Import local modules
from dcc_mcp_maya.api import maya_error, maya_from_exception, maya_success

# Import built-in modules

def execute_mel(code: str) -> dict:
    """Execute a MEL expression and return its string result.

    Args:
        code: MEL code to execute.

    Returns:
        ActionResultModel dict with ``context.output`` (str) and ``context.script``.
    """

    if not code or not code.strip():
        return maya_error("No MEL code provided", "Provide 'code' with valid MEL.")

    try:
        import maya.mel as mel  # noqa: PLC0415

        raw = mel.eval(code)
        output = str(raw) if raw is not None else ""
        return maya_success(
            "MEL executed successfully",
            prompt="MEL script finished. Check 'output' for any return value.",
            output=output,
            script=code,
        )
    except ImportError:
        return maya_error("Maya not available", "maya.mel could not be imported")
    except Exception as exc:
                return maya_from_exception(exc, "MEL execution failed")

def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`execute_mel`."""
    return execute_mel(**kwargs)

if __name__ == "__main__":
    import json

    result = execute_mel("polySphere -n mySphere;")
    print(json.dumps(result))
