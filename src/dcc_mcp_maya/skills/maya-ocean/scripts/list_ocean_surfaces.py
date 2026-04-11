"""List all Maya ocean surfaces and their associated shaders."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging

logger = logging.getLogger(__name__)


def list_ocean_surfaces() -> dict:
    """List all oceanShader nodes and find their connected geometry.

    Returns:
        ActionResultModel dict with ``context.surfaces`` (list of dicts)
        and ``context.count``.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        ocean_shaders = cmds.ls(type="oceanShader") or []
        surfaces = []
        for shader in ocean_shaders:
            sgs = cmds.listConnections(shader, type="shadingEngine") or []
            meshes = []
            for sg in sgs:
                members = cmds.sets(sg, query=True) or []
                meshes.extend(members)

            wave_height = None
            if cmds.attributeQuery("waveHeight", node=shader, exists=True):
                wave_height = cmds.getAttr("{}.waveHeight".format(shader))

            surfaces.append(
                {
                    "shader": shader,
                    "connected_meshes": meshes,
                    "wave_height": wave_height,
                }
            )

        return success_result(
            "Found {} ocean surface(s)".format(len(surfaces)),
            prompt="Use set_ocean_attribute to adjust wave parameters.",
            surfaces=surfaces,
            count=len(surfaces),
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("list_ocean_surfaces failed")
        return error_result("Failed to list ocean surfaces", str(exc)).to_dict()


def main(**kwargs):
    return list_ocean_surfaces(**kwargs)


if __name__ == "__main__":
    import json

    result = list_ocean_surfaces()
    print(json.dumps(result))
