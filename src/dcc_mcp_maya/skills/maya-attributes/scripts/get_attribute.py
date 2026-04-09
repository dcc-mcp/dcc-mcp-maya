"""Get the value of an attribute on a Maya node."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging

logger = logging.getLogger(__name__)


def get_attribute(node_name: str, attribute: str) -> dict:
    """Get the value of an attribute on a Maya node.

    Args:
        node_name: Name of the Maya node.
        attribute: Attribute name (e.g. ``"translateX"``, ``"visibility"``).

    Returns:
        ActionResultModel dict with ``context.value``.
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

        raw = cmds.getAttr(full_attr)
        # Flatten single-element tuples returned for compound attrs
        if isinstance(raw, list) and len(raw) == 1 and isinstance(raw[0], tuple):
            value = list(raw[0])
        else:
            value = raw

        return success_result(
            "{}.{} = {}".format(node_name, attribute, value),
            prompt="Use set_attribute to change the value.",
            node_name=node_name,
            attribute=attribute,
            value=value,
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("get_attribute failed")
        return error_result("Failed to get attribute", str(exc)).to_dict()


def main(**kwargs):
    return get_attribute(**kwargs)


if __name__ == "__main__":
    import json

    result = get_attribute("pSphere1", "translateX")
    print(json.dumps(result))
