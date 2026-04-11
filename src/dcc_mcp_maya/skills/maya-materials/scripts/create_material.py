"""Create a Maya shading material."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging
from typing import Optional

logger = logging.getLogger(__name__)

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
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        # shader_type is legacy alias for material_type
        resolved_type = shader_type if shader_type is not None else material_type
        mat = cmds.shadingNode(resolved_type, asShader=True)
        if name:
            mat = cmds.rename(mat, name)
        sg = cmds.sets(renderable=True, noSurfaceShader=True, empty=True, name="{}_SG".format(mat))
        cmds.connectAttr("{}.outColor".format(mat), "{}.surfaceShader".format(sg), force=True)
        return success_result(
            "Created material: {}".format(mat),
            material_name=mat,
            material_type=resolved_type,
            shading_group=sg,
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("create_material failed")
        return error_result("Failed to create material", str(exc)).to_dict()


def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`create_material`."""
    return create_material(**kwargs)


if __name__ == "__main__":
    import json

    result = create_material()
    print(json.dumps(result))
