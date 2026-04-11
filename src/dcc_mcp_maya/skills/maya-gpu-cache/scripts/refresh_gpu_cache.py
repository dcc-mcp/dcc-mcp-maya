"""Force a gpuCache node to reload its file from disk."""

# Import future modules
from __future__ import annotations

# Import local modules
from dcc_mcp_core.skill import skill_entry, skill_error, skill_exception, skill_success

from dcc_mcp_maya.api import validate_node_exists


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

        err = validate_node_exists(cmds, cache_node)
        if err:
            return err

        node_type = cmds.objectType(cache_node)
        if node_type != "gpuCache":
            return skill_error(
                "Not a gpuCache node: {}".format(cache_node),
                "Expected type 'gpuCache', got '{}'".format(node_type),
            )

        file_path = cmds.getAttr("{}.cacheFileName".format(cache_node)) or ""

        # Toggle refreshAll to force reload
        cmds.setAttr("{}.refreshAll".format(cache_node), True)
        cmds.setAttr("{}.refreshAll".format(cache_node), False)

        return skill_success(
            "Refreshed GPU cache node '{}'".format(cache_node),
            prompt="If the cache still looks outdated, check that the file path is correct with list_gpu_caches.",
            cache_node=cache_node,
            file_path=file_path,
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return skill_exception(exc, message="Failed to refresh GPU cache")


@skill_entry
def main(**kwargs):
    return refresh_gpu_cache(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main
    run_main(main)
