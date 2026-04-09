"""Execute a MEL script inside Maya."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging

logger = logging.getLogger(__name__)


def execute_mel(script: str) -> dict:
    """Execute a MEL script inside Maya.

    Args:
        script: MEL code to execute.

    Returns:
        ActionResultModel dict with ``context.output`` from the script.

    Example::

        execute_mel("sphere; select -all;")
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    try:
        import maya.mel as mel  # noqa: PLC0415

        result = mel.eval(script)
        return success_result(
            "MEL executed successfully",
            output=str(result) if result is not None else "",
            script=script,
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.mel could not be imported").to_dict()
    except Exception as exc:
        logger.exception("execute_mel failed")
        return error_result("MEL execution failed", str(exc)).to_dict()


def main(**kwargs):
    return execute_mel(**kwargs)


if __name__ == "__main__":
    import json

    result = execute_mel()
    print(json.dumps(result))
