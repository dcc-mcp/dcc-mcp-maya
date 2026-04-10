"""Set an attribute on a Maya Paint Effects stroke or brush node."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging
from typing import Any

logger = logging.getLogger(__name__)


def set_brush_attribute(name: str, attribute: str, value: Any) -> dict:
    """Set an attribute on a Paint Effects stroke node.

    Common attributes: ``brush.globalScale``, ``brush.brushType``,
    ``brush.color1`` (list of 3 floats), ``brush.incandescence1`` (list of 3),
    ``pressure1``, ``strokeSampleDensity``.

    Args:
        name: Name of the stroke node or its transform.
        attribute: Attribute path (e.g. ``"brush.globalScale"`` or ``"pressure1"``).
        value: New value (scalar or list for vector/color attributes).

    Returns:
        ActionResultModel dict indicating success or failure.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    if not name:
        return error_result("Missing required parameter 'name'", "Provide the stroke node name.").to_dict()
    if not attribute:
        return error_result("Missing required parameter 'attribute'", "Provide the attribute name.").to_dict()

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not cmds.objExists(name):
            return error_result(
                "Node '{}' not found".format(name),
                "Use list_strokes to find valid stroke names.",
            ).to_dict()

        attr_path = "{}.{}".format(name, attribute)
        if isinstance(value, (list, tuple)):
            cmds.setAttr(attr_path, *value)
        else:
            cmds.setAttr(attr_path, value)

        return success_result(
            "Set {}.{} = {}".format(name, attribute, value),
            prompt="Brush attribute updated. Use list_strokes to verify the current state.",
            node=name,
            attribute=attribute,
            value=value,
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("set_brush_attribute failed")
        return error_result("Failed to set brush attribute", str(exc)).to_dict()


def main(**kwargs) -> dict:
    return set_brush_attribute(**kwargs)


if __name__ == "__main__":
    import json

    print(json.dumps(set_brush_attribute(name="stroke1", attribute="brush.globalScale", value=2.0)))
