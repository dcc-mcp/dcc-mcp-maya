"""List all shading engine (shadingEngine) nodes in the current scene."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging

logger = logging.getLogger(__name__)

_SUPPORTED_SHADERS = ("lambert", "blinn", "phong", "phongE", "aiStandardSurface")


def list_shading_groups() -> dict:
    """List all shading engine (shadingEngine) nodes in the current scene.

    Provides a scene-level view of every shading group, including the
    assigned surface shader and the number of members.

    Returns:
        ActionResultModel dict with ``context.shading_groups`` — a list of
        dicts with ``name``, ``surface_shader``, ``shader_type``,
        ``member_count`` keys, and ``context.count``.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        sgs = cmds.ls(type="shadingEngine") or []
        result = []
        for sg in sgs:
            shaders = cmds.listConnections("{}.surfaceShader".format(sg)) or []
            surface_shader = shaders[0] if shaders else ""
            shader_type = cmds.nodeType(surface_shader) if surface_shader else ""
            try:
                members = cmds.sets(sg, query=True) or []
                member_count = len(members)
            except Exception:
                member_count = 0
            result.append(
                {
                    "name": sg,
                    "surface_shader": surface_shader,
                    "shader_type": shader_type,
                    "member_count": member_count,
                }
            )

        return success_result(
            "Found {} shading group(s)".format(len(result)),
            shading_groups=result,
            count=len(result),
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("list_shading_groups failed")
        return error_result("Failed to list shading groups", str(exc)).to_dict()


def main(**kwargs):
    return list_shading_groups(**kwargs)


if __name__ == "__main__":
    import json

    result = list_shading_groups()
    print(json.dumps(result))
