"""Delete a Maya expression node by name."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging

logger = logging.getLogger(__name__)


def delete_expression(
    expression_name: str,
) -> dict:
    """Delete a Maya expression node by name.

    Args:
        expression_name: Name of the expression node to delete.

    Returns:
        ActionResultModel dict with ``context.expression_name``.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not cmds.objExists(expression_name):
            return error_result(
                "Expression not found: {}".format(expression_name),
                "'{}' does not exist in the scene".format(expression_name),
            ).to_dict()

        node_type = cmds.objectType(expression_name)
        if node_type != "expression":
            return error_result(
                "Not an expression node: {}".format(expression_name),
                "'{}' is of type '{}', expected 'expression'".format(expression_name, node_type),
            ).to_dict()

        cmds.delete(expression_name)

        return success_result(
            "Deleted expression '{}'".format(expression_name),
            expression_name=expression_name,
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("delete_expression failed")
        return error_result("Failed to delete expression {}".format(expression_name), str(exc)).to_dict()


def main(**kwargs):
    return delete_expression(**kwargs)


if __name__ == "__main__":
    import json

    result = delete_expression()
    print(json.dumps(result))
