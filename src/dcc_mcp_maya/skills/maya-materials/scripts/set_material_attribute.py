"""Set an attribute on a material node."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging
from typing import Any

logger = logging.getLogger(__name__)

_SUPPORTED_SHADERS = ("lambert", "blinn", "phong", "phongE", "aiStandardSurface")


def set_material_attribute(
    material_name: str,
    attribute: str,
    value: Any,
) -> dict:
    """Set an attribute on a material node.

    Args:
        material_name: Name of the material node.
        attribute: Attribute name (e.g. ``"color"``, ``"transparency"``).
        value: New value.  Scalar, list-of-3 (RGB), or list-of-4 (RGBA).

    Returns:
        ActionResultModel dict.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not cmds.objExists(material_name):
            return error_result(
                "Material not found: {}".format(material_name),
                "'{}' does not exist".format(material_name),
            ).to_dict()

        attr_path = "{}.{}".format(material_name, attribute)
        if isinstance(value, (list, tuple)):
            cmds.setAttr(attr_path, *value, type="double3" if len(value) == 3 else "double4")
        else:
            cmds.setAttr(attr_path, value)

        return success_result(
            "Set {}.{} = {}".format(material_name, attribute, value),
            material_name=material_name,
            attribute=attribute,
            value=value,
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("set_material_attribute failed")
        return error_result("Failed to set material attribute", str(exc)).to_dict()


def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`set_material_attribute`."""
    return set_material_attribute(**kwargs)


if __name__ == "__main__":
    import json

    result = set_material_attribute()
    print(json.dumps(result))
