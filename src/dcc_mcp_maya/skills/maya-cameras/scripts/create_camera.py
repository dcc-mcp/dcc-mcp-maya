"""Create a new Maya camera."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging
from typing import List, Optional

logger = logging.getLogger(__name__)


def create_camera(
    name: Optional[str] = None,
    focal_length: float = 35.0,
    position: Optional[List[float]] = None,
    rotation: Optional[List[float]] = None,
) -> dict:
    """Create a new Maya camera.

    Args:
        name: Optional transform name for the new camera.
        focal_length: Camera focal length in mm.  Default: 35.0.
        position: World-space position ``[x, y, z]``.  Default: origin.
        rotation: Euler rotation ``[rx, ry, rz]`` in degrees.  Default: none.

    Returns:
        ActionResultModel dict with ``context.camera_name`` (transform) and
        ``context.camera_shape``.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        result = cmds.camera()
        transform = result[0]
        shape = result[1]

        if name:
            transform = cmds.rename(transform, name)
            # Shape is renamed automatically
            shapes = cmds.listRelatives(transform, shapes=True) or []
            shape = shapes[0] if shapes else shape

        cmds.setAttr("{}.focalLength".format(shape), focal_length)

        if position and len(position) >= 3:
            cmds.setAttr(
                "{}.translate".format(transform),
                position[0],
                position[1],
                position[2],
                type="double3",
            )
        if rotation and len(rotation) >= 3:
            cmds.setAttr(
                "{}.rotate".format(transform),
                rotation[0],
                rotation[1],
                rotation[2],
                type="double3",
            )

        return success_result(
            "Created camera '{}'".format(transform),
            camera_name=transform,
            camera_shape=shape,
            focal_length=focal_length,
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("create_camera failed")
        return error_result("Failed to create camera", str(exc)).to_dict()



def main(**kwargs):
    return create_camera(**kwargs)


if __name__ == "__main__":
    import json
    result = create_camera()
    print(json.dumps(result))
