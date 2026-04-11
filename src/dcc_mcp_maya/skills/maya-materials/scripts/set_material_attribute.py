"""Set an attribute on a material node."""

# Import future modules
from __future__ import annotations

# Import built-in modules
from typing import Any

# Import local modules
from dcc_mcp_core.skill import skill_entry, skill_error, skill_exception, skill_success

from dcc_mcp_maya.api import validate_node_exists

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
    try:
        import maya.cmds as cmds  # noqa: PLC0415

        err = validate_node_exists(cmds, material_name)
        if err:
            return err

        attr_path = "{}.{}".format(material_name, attribute)
        if isinstance(value, (list, tuple)):
            cmds.setAttr(attr_path, *value, type="double3" if len(value) == 3 else "double4")
        else:
            cmds.setAttr(attr_path, value)

        return skill_success(
            "Set {}.{} = {}".format(material_name, attribute, value),
            material_name=material_name,
            attribute=attribute,
            value=value,
            prompt="Use get_material_connections to verify or render_frame to preview.",
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return skill_exception(exc, message="Failed to set material attribute")


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`set_material_attribute`."""
    return set_material_attribute(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
