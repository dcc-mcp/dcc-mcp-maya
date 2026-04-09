"""Set the value of an attribute on a Maya node."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging

logger = logging.getLogger(__name__)


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
                "'{}.{}' does not exist on this node".format(node_name, attribute),
            ).to_dict()

        if isinstance(value, str):
            cmds.setAttr(full_attr, value, type="string")
        elif isinstance(value, (list, tuple)):
            cmds.setAttr(full_attr, *value)
        else:
            cmds.setAttr(full_attr, value)

        return success_result(
            "Set {}.{} = {}".format(node_name, attribute, value),
            prompt="Use get_attribute to verify the new value.",
            node_name=node_name,
            attribute=attribute,
            value=value,
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("set_attribute failed")
        return error_result("Failed to set attribute", str(exc)).to_dict()


def main(**kwargs):
    return set_attribute(**kwargs)


if __name__ == "__main__":
    import json

    result = set_attribute("pSphere1", "translateX", 5.0)
    print(json.dumps(result))
