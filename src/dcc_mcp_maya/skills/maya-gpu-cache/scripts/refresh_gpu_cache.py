"""Force a gpuCache node to reload its file from disk."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging

logger = logging.getLogger(__name__)


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
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not cmds.objExists(cache_node):
            return error_result(
                "GPU cache node not found: {}".format(cache_node),
                "'{}' does not exist in the scene".format(cache_node),
            ).to_dict()

        node_type = cmds.objectType(cache_node)
        if node_type != "gpuCache":
            return error_result(
                "Not a gpuCache node: {}".format(cache_node),
                "Expected type 'gpuCache', got '{}'".format(node_type),
            ).to_dict()

        file_path = cmds.getAttr("{}.cacheFileName".format(cache_node)) or ""

        # Toggle refreshAll to force reload
        cmds.setAttr("{}.refreshAll".format(cache_node), True)
        cmds.setAttr("{}.refreshAll".format(cache_node), False)

        return success_result(
            "Refreshed GPU cache node '{}'".format(cache_node),
            prompt="If the cache still looks outdated, check that the file path is correct with list_gpu_caches.",
            cache_node=cache_node,
            file_path=file_path,
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("refresh_gpu_cache failed")
        return error_result("Failed to refresh GPU cache", str(exc)).to_dict()


def main(**kwargs):
    return refresh_gpu_cache(**kwargs)


if __name__ == "__main__":
    import json

    print(json.dumps(refresh_gpu_cache("gpuCacheShape1"), indent=2))
