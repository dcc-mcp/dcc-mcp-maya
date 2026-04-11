"""Delete an expression node from the Maya scene."""

# Import future modules
from __future__ import annotations

# Import built-in modules
# Import local modules
from dcc_mcp_maya.api import maya_error, maya_from_exception, maya_success


def delete_expression(name: str) -> dict:
    """Delete an expression node by name.

    Args:
        name: Expression node name to delete.

    Returns:
        ActionResultModel dict with ``context.expression_name`` confirming deletion.
    """
    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not cmds.objExists(name):
            return maya_error(
                "Expression node '{}' does not exist".format(name),
                "Use list_expressions to see available expression nodes.",
            )

        # Verify it is actually an expression node
        node_type = cmds.objectType(name)
        if node_type != "expression":
            return maya_error(
                "Node '{}' is not an expression (type: {})".format(name, node_type),
                "Provide an expression node name. Use list_expressions to find them.",
            )

        cmds.delete(name)
        return maya_success(
            "Expression node '{}' deleted".format(name),
            prompt="Expression removed. Driven attributes will retain their last evaluated values.",
            expression_name=name,
            deleted_node=name,
        )
    except ImportError:
        return maya_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return maya_from_exception(exc, "Failed to delete expression '{}'".format(name))


def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`delete_expression`."""
    return delete_expression(**kwargs)


if __name__ == "__main__":
    import json

    result = delete_expression("expression1")
    print(json.dumps(result))
