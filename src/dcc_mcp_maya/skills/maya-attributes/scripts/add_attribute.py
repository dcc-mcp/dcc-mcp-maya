"""Add a custom attribute to a Maya node."""

# Import future modules
from __future__ import annotations

# Import built-in modules
from typing import Optional

# Import local modules
from dcc_mcp_core.skill import skill_entry, skill_error, skill_exception, skill_success

from dcc_mcp_maya.api import validate_node_exists

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
    try:
        import maya.cmds as cmds  # noqa: PLC0415

        err = validate_node_exists(cmds, node_name)
        if err:
            return err

        if attr_type not in _VALID_TYPES:
            return skill_error(
                "Invalid attribute type: {}".format(attr_type),
                "Supported types: {}".format(", ".join(sorted(_VALID_TYPES))),
            )

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

        return skill_success(
            "Added attribute '{}.{}'".format(node_name, attribute),
            prompt="Use set_attribute to assign a value to the new attribute.",
            node_name=node_name,
            attribute=attribute,
            attr_type=attr_type,
            keyable=keyable,
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return skill_exception(exc, message="Failed to add attribute")


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`add_attribute`."""
    return add_attribute(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main
    run_main(main)
