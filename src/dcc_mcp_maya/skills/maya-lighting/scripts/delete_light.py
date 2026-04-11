"""Delete a light from the scene by transform name."""

# Import future modules
from __future__ import annotations

# Import local modules
from dcc_mcp_maya.api import maya_error, maya_from_exception, maya_success

# Supported Maya light types and their corresponding command/node names
_LIGHT_TYPE_MAP = {
    "point": "pointLight",
    "spot": "spotLight",
    "directional": "directionalLight",
    "area": "areaLight",
    "ambient": "ambientLight",
}


def delete_light(light_name: str) -> dict:
    """Delete a light from the scene by transform name.

    Args:
        light_name: Name of the light transform to delete.

    Returns:
        ActionResultModel dict.
    """
    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not cmds.objExists(light_name):
            return maya_error(
                "Light not found: {}".format(light_name),
                "'{}' does not exist in the scene".format(light_name),
            )

        node_type = cmds.objectType(light_name)
        # If it's a shape, delete its transform
        if node_type not in ("transform",):
            parents = cmds.listRelatives(light_name, parent=True)
            if parents:
                light_name = parents[0]

        cmds.delete(light_name)
        return maya_success("Deleted light '{}'".format(light_name), light_name=light_name)
    except ImportError:
        return maya_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return maya_from_exception(exc, "Failed to delete light")


def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`delete_light`."""
    return delete_light(**kwargs)


if __name__ == "__main__":
    import json

    result = delete_light()
    print(json.dumps(result))
