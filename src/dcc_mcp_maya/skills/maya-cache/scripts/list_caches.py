"""List all cache nodes attached to objects in the Maya scene."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging

logger = logging.getLogger(__name__)


def list_caches() -> dict:
    """List all cache nodes (cacheFile, cacheBlend, AlembicNode) in the scene.

    Returns:
        ActionResultModel dict with ``context.caches`` (list of dicts) and
        ``context.count``.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        cache_types = ("cacheFile", "cacheBlend", "AlembicNode")
        items = []
        for cache_type in cache_types:
            nodes = cmds.ls(type=cache_type) or []
            for node in nodes:
                info = {"node": node, "cache_type": cache_type}
                # Try to get file path
                try:
                    if cache_type == "cacheFile":
                        info["file_path"] = cmds.getAttr("{}.cachePath".format(node)) or ""
                    elif cache_type == "AlembicNode":
                        info["file_path"] = cmds.getAttr("{}.fileName".format(node)) or ""
                    else:
                        info["file_path"] = ""
                except Exception:
                    info["file_path"] = ""
                items.append(info)

        return success_result(
            "Found {} cache node(s)".format(len(items)),
            prompt="Use delete_cache to remove a cache or import_alembic to add Alembic caches.",
            caches=items,
            count=len(items),
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("list_caches failed")
        return error_result("Failed to list caches", str(exc)).to_dict()


def main(**kwargs) -> dict:
    return list_caches(**kwargs)


if __name__ == "__main__":
    import json

    print(json.dumps(list_caches()))
