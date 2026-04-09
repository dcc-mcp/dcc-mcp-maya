"""Get the value of an attribute on a Maya node."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging
from typing import Any

logger = logging.getLogger(__name__)


def get_attribute(
    object_name: str,
    attribute: str,
) -> dict:
    """Get the value of an attribute on a Maya node.

    Supports numeric, string, boolean, and compound (vector/matrix) attributes.

    Args:
        object_name: Name of the Maya node.
        attribute: Attribute name (e.g. ``"translateX"``, ``"visibility"``,
            ``"color"``).

    Returns:
        ActionResultModel dict with ``context.value`` containing the attribute
        value.
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
                "The attribute '{}' does not exist on node '{}'".format(attribute, object_name),
            ).to_dict()

        raw = cmds.getAttr(full_attr)

        # Normalise compound results (list of tuples → flat list)
        if isinstance(raw, list) and raw and isinstance(raw[0], tuple):
            value = list(raw[0])
        else:
            value = raw

        return success_result(
            "Got {}.{} = {}".format(object_name, attribute, value),
            object_name=object_name,
            attribute=attribute,
            value=value,
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("get_attribute failed")
        return error_result(
            "Failed to get attribute {}.{}".format(object_name, attribute),
            str(exc),
        ).to_dict()



def main(**kwargs):
    return get_attribute(**kwargs)


if __name__ == "__main__":
    import json
    result = get_attribute()
    print(json.dumps(result))
