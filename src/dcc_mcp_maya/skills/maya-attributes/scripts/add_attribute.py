"""Add a custom attribute to a Maya node."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging
from typing import Optional

logger = logging.getLogger(__name__)

_VALID_TYPES = {
    "float",
    "double",
    "long",
    "short",
    "bool",
    "string",
    "float3",
    "double3",
    "long3",
    "short3",
    "enum",
    "message",
}


def add_attribute(
    node_name: str,
    attribute: str,
    attr_type: str = "float",
    default_value: Optional[object] = None,
    min_value: Optional[float] = None,
    max_value: Optional[float] = None,
    keyable: bool = True,
) -> dict:
    """Add a custom attribute to a Maya node.

    Args:
        node_name: Name of the Maya node.
        attribute: Long name for the new attribute.
        attr_type: Attribute data type.  One of: ``float``, ``double``,
            ``long``, ``short``, ``bool``, ``string``, ``float3``, ``double3``,
            ``long3``, ``short3``, ``enum``, ``message``.
        default_value: Default value for numeric attributes.
        min_value: Minimum value (numeric types only).
        max_value: Maximum value (numeric types only).
        keyable: Whether the attribute should appear in the Channel Box.

    Returns:
        ActionResultModel dict with ``context.attribute``.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not cmds.objExists(node_name):
            return error_result(
                "Node not found: {}".format(node_name),
                "'{}' does not exist".format(node_name),
            ).to_dict()

        if attr_type not in _VALID_TYPES:
            return error_result(
                "Invalid attribute type: {}".format(attr_type),
                "Supported types: {}".format(", ".join(sorted(_VALID_TYPES))),
            ).to_dict()

        kwargs = {"longName": attribute, "attributeType": attr_type, "keyable": keyable}
        if attr_type == "string":
            kwargs["dataType"] = "string"
            del kwargs["attributeType"]
        if default_value is not None and attr_type not in ("string", "message"):
            kwargs["defaultValue"] = default_value
        if min_value is not None:
            kwargs["minValue"] = min_value
        if max_value is not None:
            kwargs["maxValue"] = max_value

        cmds.addAttr(node_name, **kwargs)

        return success_result(
            "Added attribute '{}.{}'".format(node_name, attribute),
            prompt="Use set_attribute to assign a value to the new attribute.",
            node_name=node_name,
            attribute=attribute,
            attr_type=attr_type,
            keyable=keyable,
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("add_attribute failed")
        return error_result("Failed to add attribute", str(exc)).to_dict()


def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`add_attribute`."""
    return add_attribute(**kwargs)


if __name__ == "__main__":
    import json

    result = add_attribute("pSphere1", "myFloat", "float", 0.0)
    print(json.dumps(result))
