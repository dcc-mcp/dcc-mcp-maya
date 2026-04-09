"""Delete a custom (user-defined) attribute from a Maya node."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging

logger = logging.getLogger(__name__)


def delete_attribute(node_name: str, attribute: str) -> dict:
    """Delete a custom (user-defined) attribute from a Maya node.

    Built-in / locked attributes cannot be deleted and will return an error.

    Args:
        node_name: Name of the Maya node.
        attribute: Attribute name to delete.

    Returns:
        ActionResultModel dict.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not cmds.objExists(node_name):
            return error_result(
                "Node not found: {}".format(node_name),
                "'{}' does not exist".format(node_name),
            ).to_dict()

        full_attr = "{}.{}".format(node_name, attribute)
        if not cmds.objExists(full_attr):
            return error_result(
                "Attribute not found: {}".format(full_attr),
                "'{}.{}' does not exist".format(node_name, attribute),
            ).to_dict()

        if not cmds.attributeQuery(attribute, node=node_name, userDefined=True):
            return error_result(
                "Cannot delete built-in attribute",
                "'{}.{}' is a built-in attribute and cannot be deleted".format(node_name, attribute),
            ).to_dict()

        cmds.deleteAttr("{}.{}".format(node_name, attribute))

        return success_result(
            "Deleted attribute '{}.{}'".format(node_name, attribute),
            node_name=node_name,
            attribute=attribute,
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("delete_attribute failed")
        return error_result("Failed to delete attribute", str(exc)).to_dict()


def main(**kwargs):
    return delete_attribute(**kwargs)


if __name__ == "__main__":
    import json

    result = delete_attribute("pSphere1", "myFloat")
    print(json.dumps(result))
