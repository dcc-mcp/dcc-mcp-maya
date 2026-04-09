"""Set an attribute on a Maya light node."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging
from typing import List, Optional

logger = logging.getLogger(__name__)

# Supported Maya light types and their corresponding command/node names
_LIGHT_TYPE_MAP = {
    "point": "pointLight",
    "spot": "spotLight",
    "directional": "directionalLight",
    "area": "areaLight",
    "ambient": "ambientLight",
}


def set_light_attribute(
    light_name: str,
    attribute: str,
    value: object,
) -> dict:
    """Set an attribute on a Maya light node.

    This function accepts either the transform or the shape name.  It will
    automatically resolve the shape node when needed.

    Common attributes: ``"intensity"``, ``"color"``, ``"coneAngle"`` (spot),
    ``"penumbraAngle"`` (spot), ``"dropoff"`` (spot), ``"shadowColor"``,
    ``"useDepthMapShadows"``.

    Args:
        light_name: Name of the light transform or shape.
        attribute: Attribute name (e.g. ``"intensity"``).
        value: New value.  Lists/tuples are expanded as ``double3`` vectors.

    Returns:
        ActionResultModel dict.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not cmds.objExists(light_name):
            return error_result("Light not found: {}".format(light_name)).to_dict()

        # Try to resolve shape for light-specific attrs
        shapes = cmds.listRelatives(light_name, shapes=True) or []
        target = shapes[0] if shapes else light_name

        full_attr = "{}.{}".format(target, attribute)
        if not cmds.objExists(full_attr):
            # Attribute may be on transform instead
            full_attr = "{}.{}".format(light_name, attribute)
        if not cmds.objExists(full_attr):
            return error_result("Attribute '{}' not found on '{}'".format(attribute, light_name)).to_dict()

        if isinstance(value, (list, tuple)) and len(value) == 3:
            cmds.setAttr(full_attr, value[0], value[1], value[2], type="double3")
        elif isinstance(value, str):
            cmds.setAttr(full_attr, value, type="string")
        else:
            cmds.setAttr(full_attr, value)

        return success_result(
            "Set {}.{} = {}".format(light_name, attribute, value),
            light_name=light_name,
            attribute=attribute,
            value=value,
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("set_light_attribute failed")
        return error_result("Failed to set light attribute", str(exc)).to_dict()



def main(**kwargs):
    return set_light_attribute(**kwargs)


if __name__ == "__main__":
    import json
    result = set_light_attribute()
    print(json.dumps(result))
