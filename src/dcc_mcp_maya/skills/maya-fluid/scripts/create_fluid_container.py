"""Create a Maya Fluid Effects container."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging
from typing import Optional

logger = logging.getLogger(__name__)


def create_fluid_container(
    name: Optional[str] = None,
    container_type: str = "3d",
    resolution_x: int = 10,
    resolution_y: int = 10,
    resolution_z: int = 10,
    size_x: float = 10.0,
    size_y: float = 10.0,
    size_z: float = 10.0,
) -> dict:
    """Create a Maya Fluid Effects container (3D or 2D).

    Args:
        name: Optional name for the fluid container node.
        container_type: ``"3d"`` for a volumetric container or ``"2d"`` for a flat container.
        resolution_x: Voxel resolution along X (3D only, minimum 1).
        resolution_y: Voxel resolution along Y (minimum 1).
        resolution_z: Voxel resolution along Z (3D only, minimum 1).
        size_x: World-space size along X.
        size_y: World-space size along Y.
        size_z: World-space size along Z.

    Returns:
        ActionResultModel dict with ``context.fluid_node`` and ``context.transform``.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    valid_types = ("3d", "2d")
    if container_type not in valid_types:
        return error_result(
            "Invalid container_type '{}'".format(container_type),
            "Supported types: 3d, 2d",
        ).to_dict()

    for val, label in ((resolution_x, "resolution_x"), (resolution_y, "resolution_y"), (resolution_z, "resolution_z")):
        if val < 1:
            return error_result(
                "Invalid {} '{}': must be >= 1".format(label, val),
                "Use a positive integer for resolution.",
            ).to_dict()

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if container_type == "3d":
            create_kwargs = {
                "resolutionX": resolution_x,
                "resolutionY": resolution_y,
                "resolutionZ": resolution_z,
                "sizeX": size_x,
                "sizeY": size_y,
                "sizeZ": size_z,
            }
        else:
            create_kwargs = {
                "resolutionX": resolution_x,
                "resolutionY": resolution_y,
                "sizeX": size_x,
                "sizeY": size_y,
            }

        if name:
            create_kwargs["name"] = name

        result = cmds.fluidContainer(**create_kwargs)
        fluid_transform = result[0] if isinstance(result, (list, tuple)) else result
        fluid_shape = cmds.listRelatives(fluid_transform, shapes=True, fullPath=False)
        fluid_node = fluid_shape[0] if fluid_shape else fluid_transform

        return success_result(
            "Created {} fluid container '{}'".format(container_type.upper(), fluid_node),
            prompt=(
                "Fluid container created. Use add_fluid_emitter to add an emitter, "
                "or set_fluid_attribute to configure density/velocity/temperature."
            ),
            fluid_node=fluid_node,
            transform=fluid_transform,
            container_type=container_type,
            resolution=[resolution_x, resolution_y, resolution_z if container_type == "3d" else 1],
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("create_fluid_container failed")
        return error_result("Failed to create fluid container", str(exc)).to_dict()


def main(**kwargs) -> dict:
    return create_fluid_container(**kwargs)


if __name__ == "__main__":
    import json

    print(json.dumps(create_fluid_container()))
