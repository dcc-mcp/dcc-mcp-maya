"""Create a 3D fluid container in the Maya scene."""

# Import future modules
from __future__ import annotations

# Import built-in modules
from typing import Optional

# Import local modules
from dcc_mcp_core.skill import skill_entry, skill_error, skill_exception, skill_success


def create_fluid_container(
    name: Optional[str] = None,
    size_x: float = 10.0,
    size_y: float = 10.0,
    size_z: float = 10.0,
    resolution: int = 10,
) -> dict:
    """Create a Maya 3D fluid container (fluidShape).

    Args:
        name: Optional name for the fluid container transform.
        size_x: X dimension of the fluid grid. Default ``10.0``.
        size_y: Y dimension of the fluid grid. Default ``10.0``.
        size_z: Z dimension of the fluid grid. Default ``10.0``.
        resolution: Voxel resolution along each axis. Default ``10``.

    Returns:
        ActionResultModel dict with ``context.fluid_transform`` and
        ``context.fluid_shape``.
    """
    try:
        import maya.cmds as cmds  # noqa: PLC0415

        cmds.create3dFluid(
            resolutionW=resolution,
            resolutionH=resolution,
            resolutionD=resolution,
            sizeX=size_x,
            sizeY=size_y,
            sizeZ=size_z,
        )

        fluid_shapes = cmds.ls(type="fluidShape") or []
        fluid_shape = fluid_shapes[-1] if fluid_shapes else ""
        fluid_transform = ""
        if fluid_shape:
            parents = cmds.listRelatives(fluid_shape, parent=True, fullPath=False) or [fluid_shape]
            fluid_transform = parents[0]
            if name:
                fluid_transform = cmds.rename(fluid_transform, name)
                shapes = cmds.listRelatives(fluid_transform, shapes=True, fullPath=False) or []
                fluid_shape = shapes[0] if shapes else fluid_shape

        return skill_success(
            "Fluid container created",
            prompt=(
                "Fluid container '{}' ready. Use set_fluid_attribute to configure "
                "density/velocity, then run simulation.".format(fluid_transform)
            ),
            fluid_transform=fluid_transform,
            fluid_shape=fluid_shape,
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return skill_exception(exc, message="Failed to create fluid container")


@skill_entry
def main(**kwargs):
    return create_fluid_container(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main
    run_main(main)
