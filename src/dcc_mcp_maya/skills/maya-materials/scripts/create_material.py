"""Create a Maya shading material."""

# Import future modules
from __future__ import annotations

# Import built-in modules
from typing import Optional

# Import local modules
from dcc_mcp_core.skill import skill_entry, skill_error, skill_exception, skill_success

_SUPPORTED_SHADERS = ("lambert", "blinn", "phong", "phongE", "aiStandardSurface")


def create_material(
    material_type: str = "lambert",
    name: Optional[str] = None,
) -> dict:
    """Create a Maya shading material.

    Args:
        material_type: Shader node type.  Supported:
            ``lambert``, ``blinn``, ``phong``, ``phongE``, ``aiStandardSurface``.
            Default: ``lambert``.
        name: Optional name for the created material.

    Returns:
        ToolResult dict with ``context.material_name`` and
        ``context.shading_group``.
    """
    try:
        import maya.cmds as cmds  # noqa: PLC0415

        mat = cmds.shadingNode(material_type, asShader=True)
        if name:
            mat = cmds.rename(mat, name)
        sg = cmds.sets(renderable=True, noSurfaceShader=True, empty=True, name="{}_SG".format(mat))
        cmds.connectAttr("{}.outColor".format(mat), "{}.surfaceShader".format(sg), force=True)
        return skill_success(
            "Created material: {}".format(mat),
            material_name=mat,
            material_type=material_type,
            shading_group=sg,
            prompt="Use assign_material to apply to objects or set_material_attribute to configure.",
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return skill_exception(exc, message="Failed to create material")


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`create_material`."""
    return create_material(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
