"""Maya scripting actions — MEL and Python execution."""

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


def execute_python(code: str) -> dict:
    """Execute Python code inside Maya's interpreter.

    The code runs in a dedicated namespace; ``import maya.cmds as cmds`` is
    pre-imported for convenience.  The last expression's string representation
    is returned as ``context.output``.

    Args:
        code: Python source code to execute.

    Returns:
        ActionResultModel dict with ``context.output`` and ``context.locals``.

    Example::

        execute_python("cmds.ls(dag=True)")
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        namespace: dict = {"cmds": cmds, "__builtins__": __builtins__}
        exec(compile(code, "<mcp-python>", "exec"), namespace)  # noqa: S102

        # Capture any "result" variable set by the code
        output = namespace.get("result", None)
        return success_result(
            "Python executed successfully",
            output=str(output) if output is not None else "",
            code=code,
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except SyntaxError as exc:
        return error_result("Python syntax error", str(exc)).to_dict()
    except Exception as exc:
        logger.exception("execute_python failed")
        return error_result("Python execution failed", str(exc)).to_dict()
