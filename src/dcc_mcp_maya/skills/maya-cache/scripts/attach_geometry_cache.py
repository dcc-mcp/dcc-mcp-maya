"""Attach an existing cache file to a mesh."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging
import os

logger = logging.getLogger(__name__)


def attach_geometry_cache(
    mesh: str,
    cache_xml_path: str,
) -> dict:
    """Attach an existing geometry cache XML file to a mesh.

    Reads the ``.xml`` cache descriptor file and connects the cache data
    to the specified mesh deformer history.

    Args:
        mesh: Name of the mesh transform or shape to attach the cache to.
        cache_xml_path: Absolute path to the ``.xml`` cache descriptor file.

    Returns:
        ActionResultModel dict with ``context.cache_node``.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    try:
        import maya.cmds as cmds  # noqa: PLC0415
        import maya.mel as mel  # noqa: PLC0415

        if not cmds.objExists(mesh):
            return error_result(
                "Mesh not found: {}".format(mesh),
                "'{}' does not exist in the scene".format(mesh),
            ).to_dict()

        if not os.path.isfile(cache_xml_path):
            return error_result(
                "Cache file not found: {}".format(cache_xml_path),
                "Ensure the .xml descriptor file exists.",
            ).to_dict()

        cmds.select(mesh)
        mel.eval('doAttachCache("{}", {{}});'.format(cache_xml_path.replace("\\", "/")))

        cache_nodes = cmds.ls(type="cacheFile") or []

        return success_result(
            "Attached cache '{}' to '{}'".format(os.path.basename(cache_xml_path), mesh),
            prompt="Use list_geometry_caches to verify the cache attachment.",
            mesh=mesh,
            cache_xml_path=cache_xml_path,
            cache_nodes=cache_nodes,
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("attach_geometry_cache failed")
        return error_result("Failed to attach geometry cache", str(exc)).to_dict()


def main(**kwargs):
    return attach_geometry_cache(**kwargs)


if __name__ == "__main__":
    import json

    result = attach_geometry_cache("pSphere1", "/tmp/cache/sphere_cache.xml")
    print(json.dumps(result))
