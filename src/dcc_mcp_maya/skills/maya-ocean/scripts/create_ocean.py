"""Create a Maya ocean surface using the oceanShader."""

# Import future modules
from __future__ import annotations

# Import built-in modules
# Import local modules
from dcc_mcp_core.skill import skill_entry, skill_error, skill_exception, skill_success


def create_ocean(
    name: str = "ocean_surface",
    subdivisions_x: int = 50,
    subdivisions_z: int = 50,
    scale: float = 100.0,
) -> dict:
    """Create a Maya ocean surface plane with an oceanShader applied.

    Args:
        name: Name for the ocean transform node. Default ``'ocean_surface'``.
        subdivisions_x: Plane subdivisions in X direction. Default ``50``.
        subdivisions_z: Plane subdivisions in Z direction. Default ``50``.
        scale: Uniform scale of the ocean plane in scene units. Default ``100.0``.

    Returns:
        ToolResult dict with ``context.ocean_transform``,
        ``context.shader_name``, and ``context.shading_group``.
    """

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        plane_result = cmds.polyPlane(
            name=name,
            subdivisionsX=subdivisions_x,
            subdivisionsHeight=subdivisions_z,
            width=scale,
            height=scale,
        )
        ocean_transform = plane_result[0]

        shader = cmds.shadingNode("oceanShader", asShader=True, name="{}_shader".format(name))
        shading_group = cmds.sets(
            renderable=True,
            noSurfaceShader=True,
            empty=True,
            name="{}_SG".format(name),
        )
        cmds.connectAttr(
            "{}.outColor".format(shader),
            "{}.surfaceShader".format(shading_group),
            force=True,
        )
        cmds.sets(ocean_transform, edit=True, forceElement=shading_group)

        return skill_success(
            "Ocean surface created",
            prompt=(
                "Ocean surface '{}' created with shader '{}'. "
                "Use set_ocean_attribute to adjust wave parameters.".format(ocean_transform, shader)
            ),
            ocean_transform=ocean_transform,
            shader_name=shader,
            shading_group=shading_group,
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return skill_exception(exc, message="Failed to create ocean surface")


@skill_entry
def main(**kwargs):
    return create_ocean(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
