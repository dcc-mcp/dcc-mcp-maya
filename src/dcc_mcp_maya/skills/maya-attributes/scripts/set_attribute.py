"""Set the value of an attribute on a Maya node."""

# Import future modules
from __future__ import annotations

# Import built-in modules

# Import local modules
from dcc_mcp_maya.api import maya_error, maya_from_exception, maya_success


def set_attribute(node_name: str, attribute: str, value: object) -> dict:
    """Set the value of an attribute on a Maya node.

    Handles scalar, boolean, string, and simple vector values.

    Args:
        node_name: Name of the Maya node.
        attribute: Attribute name (e.g. ``"translateX"``, ``"visibility"``).
        value: New value.  Strings are set with ``setAttr -type "string"``.

    Returns:
        ActionResultModel dict with ``context.node_name``, ``context.attribute``,
        and ``context.value``.
    """
    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not cmds.objExists(node_name):
            return maya_error(
                "Node not found: {}".format(node_name),
                "'{}' does not exist".format(node_name),
            )

        full_attr = "{}.{}".format(node_name, attribute)
        if not cmds.objExists(full_attr):
            return maya_error(
                "Attribute not found: {}".format(full_attr),
                "'{}.{}' does not exist on this node".format(node_name, attribute),
            )

        if isinstance(value, str):
            cmds.setAttr(full_attr, value, type="string")
        elif isinstance(value, (list, tuple)):
            cmds.setAttr(full_attr, *value)
        else:
            cmds.setAttr(full_attr, value)

        return maya_success(
            "Set {}.{} = {}".format(node_name, attribute, value),
            prompt="Use get_attribute to verify the new value.",
            node_name=node_name,
            attribute=attribute,
            value=value,
        )
    except ImportError:
        return maya_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return maya_from_exception(exc, "Failed to set attribute")


def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`set_attribute`."""
    return set_attribute(**kwargs)


if __name__ == "__main__":
    import json

    result = set_attribute("pSphere1", "translateX", 5.0)
    print(json.dumps(result))
