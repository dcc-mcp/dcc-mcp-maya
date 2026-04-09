"""Assign the built-in lambert1 to an object, resetting to default material."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging

logger = logging.getLogger(__name__)

_SUPPORTED_SHADERS = ("lambert", "blinn", "phong", "phongE", "aiStandardSurface")


def reset_to_default_material(object_name: str) -> dict:
    """Assign the built-in ``lambert1`` (initialShadingGroup) to an object.

    This effectively resets the object to Maya's default material, removing
    any previously assigned custom material.

    Args:
        object_name: Transform or mesh node name to reset.

    Returns:
        ActionResultModel dict with ``context.object_name``.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not cmds.objExists(object_name):
            return error_result(
                "Object not found: {}".format(object_name),
                "'{}' does not exist in the scene".format(object_name),
            ).to_dict()

        cmds.sets(object_name, edit=True, forceElement="initialShadingGroup")

        return success_result(
            "Reset '{}' to default material (lambert1)".format(object_name),
            object_name=object_name,
            shading_group="initialShadingGroup",
            material="lambert1",
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("reset_to_default_material failed")
        return error_result("Failed to reset material for '{}'".format(object_name), str(exc)).to_dict()


def main(**kwargs):
    return reset_to_default_material(**kwargs)


if __name__ == "__main__":
    import json

    result = reset_to_default_material()
    print(json.dumps(result))
