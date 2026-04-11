"""Rotate an HDRI environment dome around the Y axis."""

# Import future modules
from __future__ import annotations

# Import local modules
from dcc_mcp_core.skill import skill_entry, skill_error, skill_exception, skill_success

from dcc_mcp_maya.api import validate_node_exists


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

        err = validate_node_exists(cmds, light_node)
        if err:
            return err

        # Resolve transform
        node_type = cmds.objectType(light_node)
        if node_type == "transform":
            transform = light_node
        else:
            parents = cmds.listRelatives(light_node, parent=True) or []
            transform = parents[0] if parents else light_node

        cmds.setAttr("{}.rotateY".format(transform), rotation_y)

        return skill_success(
            "HDRI rotation set to {}° on '{}'".format(rotation_y, transform),
            prompt="Use set_hdri_exposure to adjust brightness or list_hdri_nodes to inspect.",
            light_node=transform,
            rotation_y=rotation_y,
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return skill_exception(exc, message="Failed to set HDRI rotation")


@skill_entry
def main(**kwargs):
    return set_hdri_rotation(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main
    run_main(main)
