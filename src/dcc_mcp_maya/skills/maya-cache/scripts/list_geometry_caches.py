"""List cache nodes attached to a mesh."""

# Import future modules
from __future__ import annotations

# Import built-in modules
from typing import Optional

# Import local modules
from dcc_mcp_core.skill import skill_entry, skill_error, skill_exception, skill_success


def list_geometry_caches(mesh: Optional[str] = None) -> dict:
    """List geometry cache nodes in the scene.

    Args:
        mesh: If provided, only cache nodes connected to this mesh are listed.
            If None, all ``cacheFile`` nodes in the scene are listed.

    Returns:
        ActionResultModel dict with ``context.cache_nodes`` (list of dicts
        with ``node``, ``cache_path``, ``start_frame``, ``end_frame``) and
        ``context.count``.
    """
    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if mesh and not cmds.objExists(mesh):
            return skill_error(
                "Mesh not found: {}".format(mesh),
                "'{}' does not exist in the scene".format(mesh),
            )

        all_cache_nodes = cmds.ls(type="cacheFile") or []

        if mesh:
            shapes = cmds.listRelatives(mesh, shapes=True) or [mesh]
            connected = set()
            for shape in shapes:
                conns = cmds.listConnections(shape, type="cacheFile") or []
                connected.update(conns)
            cache_nodes_list = [n for n in all_cache_nodes if n in connected]
        else:
            cache_nodes_list = all_cache_nodes

        result = []
        for node in cache_nodes_list:
            cache_path = cmds.getAttr("{}.cachePath".format(node)) or ""
            cache_name = cmds.getAttr("{}.cacheName".format(node)) or ""
            start_frame = cmds.getAttr("{}.sourceStart".format(node)) or 0
            end_frame = cmds.getAttr("{}.sourceEnd".format(node)) or 0
            result.append(
                {
                    "node": node,
                    "cache_path": cache_path,
                    "cache_name": cache_name,
                    "start_frame": start_frame,
                    "end_frame": end_frame,
                }
            )

        return skill_success(
            "Found {} cache node(s)".format(len(result)),
            prompt="Use delete_geometry_cache to remove a cache, or attach_geometry_cache to add one.",
            cache_nodes=result,
            count=len(result),
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return skill_exception(exc, message="Failed to list geometry caches")


@skill_entry
def main(**kwargs):
    return list_geometry_caches(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main
    run_main(main)
