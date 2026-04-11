"""List all gpuCache nodes in the scene."""

# Import future modules
from __future__ import annotations

# Import local modules
from dcc_mcp_core.skill import skill_entry, skill_error, skill_exception, skill_success


def list_gpu_caches() -> dict:
    """List all gpuCache nodes currently loaded in the scene.

    Returns:
        ActionResultModel dict with ``context.caches`` (list of dicts with
        ``transform``, ``cache_node``, and ``file_path`` keys) and ``context.count``.
    """
    try:
        import maya.cmds as cmds  # noqa: PLC0415

        nodes = cmds.ls(type="gpuCache") or []
        caches = []
        for node in nodes:
            file_path = cmds.getAttr("{}.cacheFileName".format(node)) or ""
            parents = cmds.listRelatives(node, parent=True) or []
            transform = parents[0] if parents else ""
            caches.append(
                {
                    "transform": transform,
                    "cache_node": node,
                    "file_path": file_path,
                }
            )

        return skill_success(
            "Found {} gpuCache node(s)".format(len(caches)),
            prompt="Use refresh_gpu_cache to reload a cache from disk, or import_gpu_cache to add a new one.",
            caches=caches,
            count=len(caches),
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return skill_exception(exc, message="Failed to list GPU caches")


@skill_entry
def main(**kwargs):
    return list_gpu_caches(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
