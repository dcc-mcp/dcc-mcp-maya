"""Force a gpuCache node to reload its file from disk."""

# Import future modules
from __future__ import annotations

# Import local modules
from dcc_mcp_maya.api import maya_error, maya_from_exception, maya_success


def refresh_gpu_cache(cache_node: str) -> dict:
    """Reload a GPU cache node from its file path.

    Triggers a file reload by toggling a refresh attribute, which forces Maya
    to re-read the Alembic data from disk.

    Args:
        cache_node: Name of the ``gpuCache`` shape node to refresh.

    Returns:
        ActionResultModel dict with ``context.cache_node`` and
        ``context.file_path``.
    """
    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not cmds.objExists(cache_node):
            return maya_error(
                "GPU cache node not found: {}".format(cache_node),
                "'{}' does not exist in the scene".format(cache_node),
            )

        node_type = cmds.objectType(cache_node)
        if node_type != "gpuCache":
            return maya_error(
                "Not a gpuCache node: {}".format(cache_node),
                "Expected type 'gpuCache', got '{}'".format(node_type),
            )

        file_path = cmds.getAttr("{}.cacheFileName".format(cache_node)) or ""

        # Toggle refreshAll to force reload
        cmds.setAttr("{}.refreshAll".format(cache_node), True)
        cmds.setAttr("{}.refreshAll".format(cache_node), False)

        return maya_success(
            "Refreshed GPU cache node '{}'".format(cache_node),
            prompt="If the cache still looks outdated, check that the file path is correct with list_gpu_caches.",
            cache_node=cache_node,
            file_path=file_path,
        )
    except ImportError:
        return maya_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return maya_from_exception(exc, "Failed to refresh GPU cache")


def main(**kwargs):
    return refresh_gpu_cache(**kwargs)


if __name__ == "__main__":
    import json

    print(json.dumps(refresh_gpu_cache("gpuCacheShape1"), indent=2))
