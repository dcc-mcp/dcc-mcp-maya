"""Detach and delete Maya nCache / geometry cache nodes."""

from __future__ import annotations

from typing import List, Optional

from dcc_mcp_core.skill import skill_entry

from dcc_mcp_maya.api import maya_error, maya_from_exception, maya_success
from dcc_mcp_maya.nucleus import NucleusContractError
from dcc_mcp_maya.nucleus import delete_cache as _delete_cache


def delete_ncache(
    cache_nodes: Optional[List[str]] = None,
    scene_nodes: Optional[List[str]] = None,
    delete_files: bool = False,
) -> dict:
    """Remove cacheFile nodes, optionally deleting the files on disk."""
    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not cache_nodes and not scene_nodes:
            return maya_error(
                "Nothing to delete",
                "delete_ncache needs cache_nodes or scene_nodes.",
                possible_solutions=[
                    "Pass cache_nodes=['cacheFile1'] for explicit cache nodes.",
                    "Pass scene_nodes=['nClothShape1'] to drop whatever cache feeds that node.",
                ],
            )

        result = _delete_cache(
            cmds,
            cache_nodes=cache_nodes,
            scene_nodes=scene_nodes,
            delete_files=delete_files,
        )
        return maya_success(
            "Deleted {} cache node(s)".format(result["count"]),
            deleted=result["deleted"],
            count=result["count"],
            delete_files=result["delete_files"],
            prompt="With the cache gone the simulation re-evaluates live; re-cache with create_ncache.",
        )
    except NucleusContractError as exc:
        return maya_error(
            "Invalid cache delete request",
            str(exc),
            possible_solutions=[
                "Check the node names with maya-node-graph describe_node or list_dynamics.",
                "A node with no attached cacheFile cannot be cleaned by scene_nodes alone.",
            ],
        )
    except ImportError:
        return maya_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return maya_from_exception(exc, message="Failed to delete nCache")


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`delete_ncache`."""
    return delete_ncache(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
