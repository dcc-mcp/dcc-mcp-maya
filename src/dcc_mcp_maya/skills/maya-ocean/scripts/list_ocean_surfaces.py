"""List all Maya ocean surfaces and their associated shaders."""

# Import future modules
from __future__ import annotations

# Import built-in modules


# Import local modules
from dcc_mcp_maya.api import maya_error, maya_from_exception, maya_success

def list_ocean_surfaces() -> dict:
    """List all oceanShader nodes and find their connected geometry.

    Returns:
        ActionResultModel dict with ``context.surfaces`` (list of dicts)
        and ``context.count``.
    """

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

        return maya_success(
            "Found {} ocean surface(s)".format(len(surfaces)),
            prompt="Use set_ocean_attribute to adjust wave parameters.",
            surfaces=surfaces,
            count=len(surfaces),
        )
    except ImportError:
        return maya_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return maya_from_exception(exc, "Failed to list ocean surfaces")

def main(**kwargs):
    return list_ocean_surfaces(**kwargs)

if __name__ == "__main__":
    import json

    result = list_ocean_surfaces()
    print(json.dumps(result))
