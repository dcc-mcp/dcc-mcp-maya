"""Execute a MEL script inside Maya."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging

logger = logging.getLogger(__name__)


def execute_mel(code: str) -> dict:
    """Execute a MEL expression and return its string result.

    Args:
        code: MEL code to execute.

    Returns:
        ActionResultModel dict with ``context.output`` (str) and ``context.script``.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    if not code or not code.strip():
        return error_result("No MEL code provided", "Provide 'code' with valid MEL.").to_dict()

    try:
        import maya.mel as mel  # noqa: PLC0415

        raw = mel.eval(code)
        output = str(raw) if raw is not None else ""
        return success_result(
            "MEL executed successfully",
            prompt="MEL script finished. Check 'output' for any return value.",
            output=output,
            script=code,
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.mel could not be imported").to_dict()
    except Exception as exc:
        logger.exception("execute_mel failed")
        return error_result("MEL execution failed", str(exc)).to_dict()


def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`execute_mel`."""
    return execute_mel(**kwargs)


if __name__ == "__main__":
    import json

    result = execute_mel("polySphere -n mySphere;")
    print(json.dumps(result))
