"""Assign the built-in lambert1 to an object, resetting to default material."""

# Import future modules
from __future__ import annotations

# Import local modules
from dcc_mcp_maya.api import maya_error, maya_from_exception, maya_success, validate_node_exists

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
    try:
        import maya.cmds as cmds  # noqa: PLC0415

        err = validate_node_exists(cmds, object_name)
        if err:
            return err

        cmds.sets(object_name, edit=True, forceElement="initialShadingGroup")

        return maya_success(
            "Reset '{}' to default material (lambert1)".format(object_name),
            object_name=object_name,
            shading_group="initialShadingGroup",
            material="lambert1",
            prompt="Use create_material and assign_material to set a new shader.",
        )
    except ImportError:
        return maya_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return maya_from_exception(exc, "Failed to reset material for '{}'".format(object_name))


def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`reset_to_default_material`."""
    return reset_to_default_material(**kwargs)


if __name__ == "__main__":
    import json

    result = reset_to_default_material()
    print(json.dumps(result))
