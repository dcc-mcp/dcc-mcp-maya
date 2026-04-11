"""Delete a custom (user-defined) attribute from a Maya node."""

# Import future modules
from __future__ import annotations

# Import built-in modules
# Import local modules
from dcc_mcp_core.skill import skill_entry, skill_error, skill_exception, skill_success

from dcc_mcp_maya.api import validate_node_exists


def delete_attribute(node_name: str, attribute: str) -> dict:
    """Delete a custom (user-defined) attribute from a Maya node.

    Built-in / locked attributes cannot be deleted and will return an error.

    Args:
        node_name: Name of the Maya node.
        attribute: Attribute name to delete.

    Returns:
        ActionResultModel dict.
    """
    try:
        import maya.cmds as cmds  # noqa: PLC0415

        err = validate_node_exists(cmds, node_name)
        if err:
            return err

        full_attr = "{}.{}".format(node_name, attribute)
        err = validate_node_exists(cmds, full_attr)
        if err:
            return err

        if not cmds.attributeQuery(attribute, node=node_name, userDefined=True):
            return skill_error(
                "Cannot delete built-in attribute",
                "'{}.{}' is a built-in attribute and cannot be deleted".format(node_name, attribute),
            )

        cmds.deleteAttr("{}.{}".format(node_name, attribute))

        return skill_success(
            "Deleted attribute '{}.{}'".format(node_name, attribute),
            node_name=node_name,
            attribute=attribute,
            prompt="Use list_custom_attributes to verify removal.",
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return skill_exception(exc, message="Failed to delete attribute")


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`delete_attribute`."""
    return delete_attribute(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main
    run_main(main)
