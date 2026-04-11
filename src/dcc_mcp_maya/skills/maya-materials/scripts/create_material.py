"""Create a Maya shading material."""

# Import future modules
from __future__ import annotations

# Import built-in modules
from typing import Optional

# Import local modules
from dcc_mcp_maya.api import maya_error, maya_from_exception, maya_success

_SUPPORTED_SHADERS = ("lambert", "blinn", "phong", "phongE", "aiStandardSurface")


def create_material(
    material_type: str = "lambert",
    shader_type: Optional[str] = None,
    name: Optional[str] = None,
) -> dict:
    """Create a Maya shading material.

    Args:
        material_type: Shader node type (preferred param name).  Supported:
            ``lambert``, ``blinn``, ``phong``, ``phongE``, ``aiStandardSurface``.
            Default: ``lambert``.
        shader_type: Alias for ``material_type`` (legacy).
        name: Optional name for the created material.

    Returns:
        ActionResultModel dict with ``context.material_name`` and
        ``context.shading_group``.
    """
    try:
        import maya.cmds as cmds  # noqa: PLC0415

        # shader_type is legacy alias for material_type
        resolved_type = shader_type if shader_type is not None else material_type
        mat = cmds.shadingNode(resolved_type, asShader=True)
        if name:
            mat = cmds.rename(mat, name)
        sg = cmds.sets(renderable=True, noSurfaceShader=True, empty=True, name="{}_SG".format(mat))
        cmds.connectAttr("{}.outColor".format(mat), "{}.surfaceShader".format(sg), force=True)
        return maya_success(
            "Created material: {}".format(mat),
            material_name=mat,
            material_type=resolved_type,
            shading_group=sg,
        )
    except ImportError:
        return maya_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return maya_from_exception(exc, "Failed to create material")


def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`create_material`."""
    return create_material(**kwargs)


if __name__ == "__main__":
    import json

    result = create_material()
    print(json.dumps(result))
