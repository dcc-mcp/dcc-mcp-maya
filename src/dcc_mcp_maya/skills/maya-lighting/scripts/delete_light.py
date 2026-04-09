"""Delete a light from the scene by transform name."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging

logger = logging.getLogger(__name__)

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
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not cmds.objExists(light_name):
            return error_result("Light not found: {}".format(light_name)).to_dict()

        node_type = cmds.objectType(light_name)
        # If it's a shape, delete its transform
        if node_type not in ("transform",):
            parents = cmds.listRelatives(light_name, parent=True)
            if parents:
                light_name = parents[0]

        cmds.delete(light_name)
        return success_result("Deleted light '{}'".format(light_name), light_name=light_name).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("delete_light failed")
        return error_result("Failed to delete light", str(exc)).to_dict()


def main(**kwargs):
    return delete_light(**kwargs)


if __name__ == "__main__":
    import json

    result = delete_light()
    print(json.dumps(result))
