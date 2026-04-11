"""List all gpuCache nodes in the scene."""

# Import future modules
from __future__ import annotations

# Import local modules
from dcc_mcp_maya.api import maya_error, maya_from_exception, maya_success


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

        return maya_success(
            "Found {} gpuCache node(s)".format(len(caches)),
            prompt="Use refresh_gpu_cache to reload a cache from disk, or import_gpu_cache to add a new one.",
            caches=caches,
            count=len(caches),
        )
    except ImportError:
        return maya_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return maya_from_exception(exc, "Failed to list GPU caches")


def main(**kwargs):
    return list_gpu_caches(**kwargs)


if __name__ == "__main__":
    import json

    print(json.dumps(list_gpu_caches(), indent=2))
