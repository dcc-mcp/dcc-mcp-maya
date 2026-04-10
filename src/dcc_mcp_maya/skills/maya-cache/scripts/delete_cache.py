"""Delete or detach a cache node from the Maya scene."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging

logger = logging.getLogger(__name__)


def delete_cache(cache_node: str, delete_files: bool = False) -> dict:
    """Delete a cache node and optionally its associated disk files.

    Args:
        cache_node: Name of the cache node to delete (``cacheFile``,
            ``cacheBlend``, or ``AlembicNode``).
        delete_files: If ``True``, also remove the cache files from disk
            (only supported for ``cacheFile`` nodes with a valid path).

    Returns:
        ActionResultModel dict with ``context.cache_node`` and
        ``context.files_deleted``.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    if not cache_node:
        return error_result("Invalid cache_node", "cache_node must not be empty").to_dict()

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not cmds.objExists(cache_node):
            return error_result(
                "Cache node not found: '{}'".format(cache_node),
                "Use list_caches to see available cache nodes.",
            ).to_dict()

        files_deleted = False
        if delete_files:
            cache_type = cmds.objectType(cache_node)
            if cache_type == "cacheFile":
                try:
                    cache_path = cmds.getAttr("{}.cachePath".format(cache_node)) or ""
                    cache_name = cmds.getAttr("{}.cacheName".format(cache_node)) or ""
                    if cache_path and cache_name:
                        # Import built-in modules
                        import glob
                        import os

                        pattern = "{}/{}.*".format(cache_path, cache_name)
                        for f in glob.glob(pattern):
                            os.remove(f)
                        files_deleted = True
                except Exception:
                    pass  # File deletion is best-effort

        cmds.delete(cache_node)

        return success_result(
            "Deleted cache node '{}'".format(cache_node),
            prompt="Cache removed. Use list_caches to verify.",
            cache_node=cache_node,
            files_deleted=files_deleted,
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("delete_cache failed")
        return error_result("Failed to delete cache", str(exc)).to_dict()


def main(**kwargs) -> dict:
    return delete_cache(**kwargs)


if __name__ == "__main__":
    import json

    print(json.dumps(delete_cache("cacheFile1")))
