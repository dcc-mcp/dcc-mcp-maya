"""Create a Maya camera."""

# Import future modules
from __future__ import annotations

# Import built-in modules
from typing import List, Optional

# Import local modules
from dcc_mcp_core.skill import skill_entry, skill_error, skill_exception, skill_success


def create_camera(
    name: Optional[str] = None,
    focal_length: float = 35.0,
    position: Optional[List[float]] = None,
    rotation: Optional[List[float]] = None,
) -> dict:
    """Create a new Maya camera.

    Args:
        name: Optional name for the camera transform node.
        focal_length: Focal length in mm.  Default 35.
        position: Optional ``[x, y, z]`` world-space position.
        rotation: Optional ``[rx, ry, rz]`` rotation in degrees.

    Returns:
        ActionResultModel dict with ``context.transform`` and ``context.shape``.
    """
    try:
        import maya.cmds as cmds  # noqa: PLC0415

        result = cmds.camera(focalLength=focal_length)
        transform = result[0]
        shape = result[1]

        if name:
            transform = cmds.rename(transform, name)
            shape = cmds.listRelatives(transform, shapes=True, fullPath=False)[0]

        if position and len(position) == 3:
            cmds.move(position[0], position[1], position[2], transform)
        if rotation and len(rotation) == 3:
            cmds.rotate(rotation[0], rotation[1], rotation[2], transform)

        return skill_success(
            "Created camera '{}'".format(transform),
            prompt="Use set_camera_attribute to change focal length, clipping planes, or film gate.",
            transform=transform,
            shape=shape,
            focal_length=focal_length,
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return skill_exception(exc, message="Failed to create camera")


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`create_camera`."""
    return create_camera(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
