"""Delete an expression node from the Maya scene."""

# Import future modules
from __future__ import annotations

# Import built-in modules
# Import local modules
from dcc_mcp_core.skill import skill_entry, skill_error, skill_exception, skill_success

from dcc_mcp_maya.api import validate_node_exists


def delete_expression(expression_name: str) -> dict:
    """Delete an expression node by name.

    Args:
        expression_name: Expression node name to delete.

    Returns:
        ToolResult dict with ``context.expression_name`` confirming deletion.
    """
    try:
        import maya.cmds as cmds  # noqa: PLC0415

        err = validate_node_exists(cmds, expression_name)
        if err:
            return err

        # Verify it is actually an expression node
        node_type = cmds.objectType(expression_name)
        if node_type != "expression":
            return skill_error(
                "Node '{}' is not an expression (type: {})".format(expression_name, node_type),
                "Provide an expression node name. Use list_expressions to find them.",
            )

        cmds.delete(expression_name)
        return skill_success(
            "Expression node '{}' deleted".format(expression_name),
            prompt="Expression removed. Driven attributes will retain their last evaluated values.",
            expression_name=expression_name,
            deleted_node=expression_name,
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return skill_exception(exc, message="Failed to delete expression '{}'".format(expression_name))


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`delete_expression`."""
    return delete_expression(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
