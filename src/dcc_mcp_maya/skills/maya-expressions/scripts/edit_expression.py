"""Edit an existing Maya expression node's string."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging
from typing import Optional

logger = logging.getLogger(__name__)


def edit_expression(
    name: str,
    expression: str,
    unit_conversion: Optional[str] = None,
) -> dict:
    """Edit the expression string of an existing expression node.

    Args:
        name: Expression node name to edit.
        expression: New MEL expression string.
        unit_conversion: Optional — ``"none"``, ``"angularOnly"``, or ``"all"``.

    Returns:
        ActionResultModel dict confirming the update.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not cmds.objExists(name):
            return error_result(
                "Expression node '{}' does not exist".format(name),
                "Use list_expressions to see available expression nodes.",
            ).to_dict()

        kwargs = {"edit": True, "string": expression}
        if unit_conversion:
            kwargs["unitConversion"] = unit_conversion

        cmds.expression(name, **kwargs)
        return success_result(
            "Expression '{}' updated".format(name),
            prompt="Expression updated. Use list_expressions to verify the change.",
            node=name,
            expression=expression,
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("edit_expression failed")
        return error_result("Failed to edit expression '{}'".format(name), str(exc)).to_dict()


def main(**kwargs):
    return edit_expression(**kwargs)


if __name__ == "__main__":
    import json
    result = edit_expression("expression1", "pSphere1.ty = cos(time);")
    print(json.dumps(result))
