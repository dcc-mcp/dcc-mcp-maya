"""Edit an existing Maya expression node's string."""

# Import future modules
from __future__ import annotations

# Import built-in modules
from typing import Optional

# Import local modules
from dcc_mcp_maya.api import maya_error, maya_from_exception, maya_success

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
    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not cmds.objExists(name):
            return maya_error(
                "Expression node '{}' does not exist".format(name),
                "Use list_expressions to see available expression nodes.",
            )

        kwargs = {"edit": True, "string": expression}
        if unit_conversion:
            kwargs["unitConversion"] = unit_conversion

        cmds.expression(name, **kwargs)
        return maya_success(
            "Expression '{}' updated".format(name),
            prompt="Expression updated. Use list_expressions to verify the change.",
            node=name,
            expression=expression,
        )
    except ImportError:
        return maya_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return maya_from_exception(exc, "Failed to edit expression '{}'".format(name))

def main(**kwargs):
    return edit_expression(**kwargs)

if __name__ == "__main__":
    import json

    result = edit_expression("expression1", "pSphere1.ty = cos(time);")
    print(json.dumps(result))
