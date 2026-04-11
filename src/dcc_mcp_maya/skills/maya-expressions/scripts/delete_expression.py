"""Delete an expression node from the Maya scene."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging

logger = logging.getLogger(__name__)


def delete_expression(name: str) -> dict:
    """Delete an expression node by name.

    Args:
        name: Expression node name to delete.

    Returns:
        ActionResultModel dict with ``context.expression_name`` confirming deletion.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not cmds.objExists(name):
            return error_result(
                "Expression node '{}' does not exist".format(name),
                "Use list_expressions to see available expression nodes.",
            ).to_dict()

        # Verify it is actually an expression node
        node_type = cmds.objectType(name)
        if node_type != "expression":
            return error_result(
                "Node '{}' is not an expression (type: {})".format(name, node_type),
                "Provide an expression node name. Use list_expressions to find them.",
            ).to_dict()

        cmds.delete(name)
        return success_result(
            "Expression node '{}' deleted".format(name),
            prompt="Expression removed. Driven attributes will retain their last evaluated values.",
            expression_name=name,
            deleted_node=name,
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("delete_expression failed")
        return error_result("Failed to delete expression '{}'".format(name), str(exc)).to_dict()


def main(**kwargs):
    return delete_expression(**kwargs)


if __name__ == "__main__":
    import json
    result = delete_expression("expression1")
    print(json.dumps(result))
