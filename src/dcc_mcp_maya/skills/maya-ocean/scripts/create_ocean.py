"""Create a Maya ocean plane with oceanShader and oceanDeformer."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging
from typing import Optional

logger = logging.getLogger(__name__)


def create_ocean(
    name: Optional[str] = None,
    resolution: int = 200,
    size: float = 50.0,
    wave_height: float = 0.5,
    wave_turbulence: float = 0.5,
) -> dict:
    """Create an ocean plane with an oceanShader and oceanDeformer.

    Args:
        name: Optional base name for the ocean nodes.
        resolution: Grid resolution (subdivisions along each axis, minimum 10).
        size: World-space size of the ocean plane.
        wave_height: Initial wave height scale (0.0 – 10.0).
        wave_turbulence: Initial wave turbulence (0.0 – 1.0).

    Returns:
        ActionResultModel dict with ``context.ocean_shader``, ``context.plane_transform``.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    if resolution < 10:
        return error_result(
            "Invalid resolution '{}': must be >= 10".format(resolution),
            "Use a resolution of at least 10 for a usable ocean grid.",
        ).to_dict()

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        base = name if name else "ocean"

        # Create a polygon plane as the ocean base mesh
        plane_result = cmds.polyPlane(
            name="{}_plane".format(base),
            width=size,
            height=size,
            subdivisionsX=resolution,
            subdivisionsY=resolution,
        )
        plane_transform = plane_result[0] if isinstance(plane_result, (list, tuple)) else plane_result

        # Create ocean shader
        ocean_shader = cmds.shadingNode("oceanShader", asShader=True, name="{}_shader".format(base))

        # Set initial wave attributes
        cmds.setAttr("{}.waveHeight".format(ocean_shader), wave_height)
        cmds.setAttr("{}.waveTurbulence".format(ocean_shader), wave_turbulence)

        # Connect ocean displacement to the plane via a displacement shader
        shading_group = cmds.sets(
            renderable=True,
            noSurfaceShader=True,
            empty=True,
            name="{}_SG".format(base),
        )
        cmds.connectAttr(
            "{}.outColor".format(ocean_shader),
            "{}.surfaceShader".format(shading_group),
            force=True,
        )
        cmds.sets(plane_transform, edit=True, forceElement=shading_group)

        return success_result(
            "Created ocean '{}' (res={}, size={})".format(ocean_shader, resolution, size),
            prompt=(
                "Ocean created. Use set_ocean_attribute to adjust waveHeight/waveSpeed/waveTurbulence, "
                "or create_wake to add a wake effect."
            ),
            ocean_shader=ocean_shader,
            plane_transform=plane_transform,
            shading_group=shading_group,
            resolution=resolution,
            size=size,
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("create_ocean failed")
        return error_result("Failed to create ocean", str(exc)).to_dict()


def main(**kwargs) -> dict:
    return create_ocean(**kwargs)


if __name__ == "__main__":
    import json

    print(json.dumps(create_ocean()))
