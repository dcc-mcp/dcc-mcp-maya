"""Import a GPU cache file and create a gpuCache node."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)


def import_gpu_cache(
    file_path: str,
    name: Optional[str] = None,
) -> dict:
    """Import a GPU cache Alembic file into the scene.

    Args:
        file_path: Path to the ``.abc`` GPU cache file.
        name: Optional name for the gpuCache transform node.

    Returns:
        ActionResultModel dict with ``context.transform_node`` and
        ``context.cache_node``.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not cmds.pluginInfo("gpuCache", query=True, loaded=True):
            cmds.loadPlugin("gpuCache")

        if not os.path.isfile(file_path):
            return error_result(
                "File not found: {}".format(file_path),
                "The GPU cache file does not exist on disk.",
            ).to_dict()

        # Create transform + gpuCache shape
        transform = cmds.createNode("transform", name=name or "gpuCache_import")
        cache_node = cmds.createNode("gpuCache", name="{}_cacheShape".format(transform), parent=transform)
        cmds.setAttr("{}.cacheFileName".format(cache_node), file_path, type="string")
        cmds.setAttr("{}.cacheGeomPath".format(cache_node), "|", type="string")

        return success_result(
            "Imported GPU cache '{}' as '{}'".format(os.path.basename(file_path), transform),
            prompt="Use refresh_gpu_cache if the file changes on disk. "
                   "Use list_gpu_caches to inspect all loaded caches.",
            transform_node=transform,
            cache_node=cache_node,
            file_path=file_path,
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("import_gpu_cache failed")
        return error_result("Failed to import GPU cache", str(exc)).to_dict()


def main(**kwargs):
    return import_gpu_cache(**kwargs)


if __name__ == "__main__":
    import json

    print(json.dumps(import_gpu_cache("/tmp/test_cache.abc"), indent=2))
