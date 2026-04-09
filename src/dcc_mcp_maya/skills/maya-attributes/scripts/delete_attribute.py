"""Delete a custom (user-defined) attribute from a Maya node."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)

# Supported attribute type tokens for addAttr -attributeType / -dataType
_SCALAR_TYPES = ("bool", "byte", "short", "long", "float", "double", "angle", "time")
_STRING_TYPES = ("string",)
_VECTOR_TYPES = ("float2", "float3", "double2", "double3")


def delete_attribute(
    object_name: str,
    attribute: str,
) -> dict:
    """Delete a custom (user-defined) attribute from a Maya node.

    Only user-defined attributes can be deleted.  Attempting to delete a
    built-in attribute (e.g. ``"translateX"``) will return an error.

    Args:
        object_name: Name of the Maya node.
        attribute: Long name of the attribute to delete.

    Returns:
        ActionResultModel dict.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not cmds.objExists(object_name):
            return error_result(
                "Object not found: {}".format(object_name),
                "'{}' does not exist in the scene".format(object_name),
            ).to_dict()

        full_attr = "{}.{}".format(object_name, attribute)
        if not cmds.objExists(full_attr):
            return error_result(
                "Attribute not found: {}".format(full_attr),
                "The attribute '{}' does not exist on '{}'".format(attribute, object_name),
            ).to_dict()

        # Only user-defined attributes have userData / dynamic flag
        user_defined = cmds.listAttr(object_name, userDefined=True) or []
        if attribute not in user_defined:
            return error_result(
                "Cannot delete built-in attribute: {}.{}".format(object_name, attribute),
                "Only user-defined (custom) attributes can be deleted",
            ).to_dict()

        cmds.deleteAttr(full_attr)
        return success_result(
            "Deleted attribute '{}.{}'".format(object_name, attribute),
            object_name=object_name,
            attribute=attribute,
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("delete_attribute failed")
        return error_result("Failed to delete attribute '{}.{}'".format(object_name, attribute), str(exc)).to_dict()



def main(**kwargs):
    return delete_attribute(**kwargs)


if __name__ == "__main__":
    import json
    result = delete_attribute()
    print(json.dumps(result))
