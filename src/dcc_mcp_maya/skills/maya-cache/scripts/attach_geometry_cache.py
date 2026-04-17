"""Attach an existing cache file to a mesh."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import os

# Import local modules
from dcc_mcp_core.skill import skill_entry, skill_error, skill_exception, skill_success

from dcc_mcp_maya.api import validate_node_exists


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
        ToolResult dict with ``context.cache_node``.
    """
    try:
        import maya.cmds as cmds  # noqa: PLC0415
        import maya.mel as mel  # noqa: PLC0415

        err = validate_node_exists(cmds, mesh)
        if err:
            return err

        if not os.path.isfile(cache_xml_path):
            return skill_error(
                "Cache file not found: {}".format(cache_xml_path),
                "Ensure the .xml descriptor file exists.",
            )

        cmds.select(mesh)
        mel.eval('doAttachCache("{}", {{}});'.format(cache_xml_path.replace("\\", "/")))

        cache_nodes = cmds.ls(type="cacheFile") or []

        return skill_success(
            "Attached cache '{}' to '{}'".format(os.path.basename(cache_xml_path), mesh),
            prompt="Use list_geometry_caches to verify the cache attachment.",
            mesh=mesh,
            cache_xml_path=cache_xml_path,
            cache_nodes=cache_nodes,
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return skill_exception(exc, message="Failed to attach geometry cache")


@skill_entry
def main(**kwargs):
    return attach_geometry_cache(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
