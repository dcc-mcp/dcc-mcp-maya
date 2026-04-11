"""Import a GPU cache file and create a gpuCache node."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import os
from typing import Optional

# Import local modules
from dcc_mcp_core.skill import skill_entry, skill_error, skill_exception, skill_success


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
    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not cmds.pluginInfo("gpuCache", query=True, loaded=True):
            cmds.loadPlugin("gpuCache")

        if not os.path.isfile(file_path):
            return skill_error(
                "File not found: {}".format(file_path),
                "The GPU cache file does not exist on disk.",
            )

        # Create transform + gpuCache shape
        transform = cmds.createNode("transform", name=name or "gpuCache_import")
        cache_node = cmds.createNode("gpuCache", name="{}_cacheShape".format(transform), parent=transform)
        cmds.setAttr("{}.cacheFileName".format(cache_node), file_path, type="string")
        cmds.setAttr("{}.cacheGeomPath".format(cache_node), "|", type="string")

        return skill_success(
            "Imported GPU cache '{}' as '{}'".format(os.path.basename(file_path), transform),
            prompt="Use refresh_gpu_cache if the file changes on disk. "
            "Use list_gpu_caches to inspect all loaded caches.",
            transform_node=transform,
            cache_node=cache_node,
            file_path=file_path,
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return skill_exception(exc, message="Failed to import GPU cache")


@skill_entry
def main(**kwargs):
    return import_gpu_cache(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main
    run_main(main)
