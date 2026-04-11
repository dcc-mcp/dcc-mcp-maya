"""Rotate an HDRI environment dome around the Y axis."""

# Import future modules
from __future__ import annotations

# Import local modules
from dcc_mcp_maya.api import maya_error, maya_from_exception, maya_success


def set_hdri_rotation(
    light_node: str,
    rotation_y: float,
) -> dict:
    """Set the Y-axis rotation of an HDRI dome light.

    Rotation is applied to the transform node so it works for both Arnold
    ``aiSkyDomeLight`` and native Maya light types.

    Args:
        light_node: Name of the dome light transform.
        rotation_y: Y-axis rotation in degrees (0-360).

    Returns:
        ActionResultModel dict with ``light_node`` and ``rotation_y``.
    """
    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not cmds.objExists(light_node):
            return maya_error(
                "Light node not found: {}".format(light_node),
                "Verify the node name with list_hdri_nodes",
            )

        # Resolve transform
        node_type = cmds.objectType(light_node)
        if node_type == "transform":
            transform = light_node
        else:
            parents = cmds.listRelatives(light_node, parent=True) or []
            transform = parents[0] if parents else light_node

        cmds.setAttr("{}.rotateY".format(transform), rotation_y)

        return maya_success(
            "HDRI rotation set to {}° on '{}'".format(rotation_y, transform),
            prompt="Use set_hdri_exposure to adjust brightness or list_hdri_nodes to inspect.",
            light_node=transform,
            rotation_y=rotation_y,
        )
    except ImportError:
        return maya_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return maya_from_exception(exc, "Failed to set HDRI rotation")


def main(**kwargs):
    return set_hdri_rotation(**kwargs)


if __name__ == "__main__":
    import json

    print(json.dumps(set_hdri_rotation("hdriDome1", 90.0)))
