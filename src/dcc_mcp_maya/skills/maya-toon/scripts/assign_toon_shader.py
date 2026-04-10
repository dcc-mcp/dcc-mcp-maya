"""Create and assign a toon-style surface shader to objects."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging
from typing import List, Optional

logger = logging.getLogger(__name__)


def assign_toon_shader(
    objects: List[str],
    color: Optional[List[float]] = None,
    name: Optional[str] = None,
) -> dict:
    """Create a flat-shading surfaceShader and assign it to the given objects.

    A ``surfaceShader`` outputs colour directly without lighting calculation,
    which gives a classic flat/toon look when combined with pfxToon outlines.

    Args:
        objects: List of mesh/transform names to assign the shader to.
        color: RGB colour for the shader (each channel 0.0 – 1.0).
               Defaults to [0.8, 0.8, 0.8].
        name: Optional name for the shader node.

    Returns:
        ActionResultModel dict with ``context.shader`` and ``context.shading_group``.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    if not objects:
        return error_result(
            "Missing required parameter 'objects'",
            "Provide at least one object name.",
        ).to_dict()

    color = color if color is not None else [0.8, 0.8, 0.8]
    if len(color) != 3:
        return error_result(
            "Invalid color '{}': must be a list of 3 floats".format(color),
            "Provide RGB values in range 0.0–1.0.",
        ).to_dict()

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        shader_name = name if name else "toonSurface"
        shader = cmds.shadingNode("surfaceShader", asShader=True, name=shader_name)
        cmds.setAttr("{}.outColor".format(shader), color[0], color[1], color[2], type="double3")

        sg = cmds.sets(
            renderable=True,
            noSurfaceShader=True,
            empty=True,
            name="{}_SG".format(shader),
        )
        cmds.connectAttr(
            "{}.outColor".format(shader),
            "{}.surfaceShader".format(sg),
            force=True,
        )

        missing = []
        assigned = []
        for obj in objects:
            if cmds.objExists(obj):
                cmds.sets(obj, edit=True, forceElement=sg)
                assigned.append(obj)
            else:
                missing.append(obj)

        if missing:
            return error_result(
                "Objects not found: {}".format(", ".join(missing)),
                "Use list_oceans or scene query to verify object names.",
            ).to_dict()

        return success_result(
            "Assigned toon shader '{}' to {} object(s)".format(shader, len(assigned)),
            prompt=(
                "Toon shader assigned. Combine with create_toon_outline for full toon look. "
                "Adjust color with set_toon_attribute on the shader."
            ),
            shader=shader,
            shading_group=sg,
            assigned=assigned,
            color=color,
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("assign_toon_shader failed")
        return error_result("Failed to assign toon shader", str(exc)).to_dict()


def main(**kwargs) -> dict:
    return assign_toon_shader(**kwargs)


if __name__ == "__main__":
    import json

    print(json.dumps(assign_toon_shader(objects=["pSphere1"], color=[1.0, 0.5, 0.0])))
