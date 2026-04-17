"""Create a ramp-based surface shader for cel shading in Maya."""

# Import future modules
from __future__ import annotations

# Import built-in modules
from typing import List, Optional

# Import local modules
from dcc_mcp_core.skill import skill_entry, skill_error, skill_exception, skill_success


def create_toon_shader(
    name: str = "toonShader1",
    color_ramp: Optional[List[List[float]]] = None,
    assign_to: Optional[List[str]] = None,
) -> dict:
    """Create a ramp-based surface shader suitable for cel shading.

    A ``rampShader`` node is created with a 3-band colour ramp (shadow, mid,
    highlight).  Optionally assigns the shader to mesh objects.

    Args:
        name: Name for the created ``rampShader`` node.
        color_ramp: List of ``[r, g, b]`` colours for ``[shadow, mid, highlight]``
            positions.  Defaults to black / mid-grey / white.
        assign_to: Optional list of mesh or transform nodes to assign the shader.

    Returns:
        ToolResult dict with the shader node name and shading group.
    """

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        shader = cmds.shadingNode("rampShader", asShader=True, name=name)

        default_ramp = [
            [0.05, 0.05, 0.05],  # shadow
            [0.45, 0.45, 0.45],  # mid
            [1.0, 1.0, 1.0],  # highlight
        ]
        ramp_colors = color_ramp if color_ramp and len(color_ramp) == 3 else default_ramp

        # Set specular colour index 0-2
        positions = [0.0, 0.5, 1.0]
        for i, (pos, col) in enumerate(zip(positions, ramp_colors)):
            try:
                cmds.setAttr("{}.color[{}].color_ColorR".format(shader, i), col[0])
                cmds.setAttr("{}.color[{}].color_ColorG".format(shader, i), col[1])
                cmds.setAttr("{}.color[{}].color_ColorB".format(shader, i), col[2])
                cmds.setAttr("{}.color[{}].color_Position".format(shader, i), pos)
            except Exception:
                pass

        sg = cmds.sets(renderable=True, noSurfaceShader=True, empty=True, name="{}_SG".format(shader))
        cmds.connectAttr(
            "{}.outColor".format(shader),
            "{}.surfaceShader".format(sg),
            force=True,
        )

        assigned_to = []
        if assign_to:
            for obj in assign_to:
                if cmds.objExists(obj):
                    cmds.sets(obj, edit=True, forceElement=sg)
                    assigned_to.append(obj)

        return skill_success(
            "Created toon shader '{}' with shading group '{}'".format(shader, sg),
            prompt="Use add_toon_outline to add ink outlines to the same meshes.",
            shader=shader,
            shading_group=sg,
            assigned_to=assigned_to,
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return skill_exception(exc, message="Failed to create toon shader")


@skill_entry
def main(**kwargs):
    return create_toon_shader(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
