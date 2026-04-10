"""Set an attribute on a Maya pfxToon outline node."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging
from typing import Any

logger = logging.getLogger(__name__)


def set_toon_attribute(name: str, attribute: str, value: Any) -> dict:
    """Set an attribute on a pfxToon node.

    Common attributes: ``profileLineWidth``, ``creaseLineWidth``,
    ``profileLineColor`` (list of 3 floats), ``hardCreasesOnly``,
    ``lineWidth``, ``creaseAngle``.

    Args:
        name: Name of the pfxToon node.
        attribute: Attribute name to set.
        value: New value (scalar or list for color/vector attributes).

    Returns:
        ActionResultModel dict indicating success or failure.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    if not name:
        return error_result("Missing required parameter 'name'", "Provide the pfxToon node name.").to_dict()
    if not attribute:
        return error_result("Missing required parameter 'attribute'", "Provide the attribute name.").to_dict()

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not cmds.objExists(name):
            return error_result(
                "Node '{}' not found".format(name),
                "Use list_toon_lines to find valid toon node names.",
            ).to_dict()

        attr_path = "{}.{}".format(name, attribute)
        if isinstance(value, (list, tuple)):
            cmds.setAttr(attr_path, *value)
        else:
            cmds.setAttr(attr_path, value)

        return success_result(
            "Set {}.{} = {}".format(name, attribute, value),
            prompt="Attribute updated. Use list_toon_lines to verify the current state.",
            node=name,
            attribute=attribute,
            value=value,
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("set_toon_attribute failed")
        return error_result("Failed to set toon attribute", str(exc)).to_dict()


def main(**kwargs) -> dict:
    return set_toon_attribute(**kwargs)


if __name__ == "__main__":
    import json

    print(json.dumps(set_toon_attribute(name="pfxToon1", attribute="profileLineWidth", value=2.0)))
