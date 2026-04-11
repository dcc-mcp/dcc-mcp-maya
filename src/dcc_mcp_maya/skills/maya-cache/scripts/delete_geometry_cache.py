"""Delete a geometry cache node and optionally its files."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import os

# Import local modules
from dcc_mcp_core.skill import skill_entry, skill_error, skill_exception, skill_success

from dcc_mcp_maya.api import validate_node_exists


def delete_geometry_cache(
    cache_node: str,
    delete_files: bool = False,
) -> dict:
    """Delete a geometry cache node from Maya.

    Removes the ``cacheFile`` node from the scene and optionally deletes
    the associated cache files from disk.

    Args:
        cache_node: Name of the ``cacheFile`` node to delete.
        delete_files: If ``True``, also delete the cache ``.xml`` and data
            files from disk.  Default ``False``.

    Returns:
        ActionResultModel dict with ``context.deleted_node`` and
        ``context.files_deleted``.
    """
    try:
        import maya.cmds as cmds  # noqa: PLC0415

        err = validate_node_exists(cmds, cache_node)
        if err:
            return err

        files_deleted = []
        if delete_files:
            cache_path = cmds.getAttr("{}.cachePath".format(cache_node)) or ""
            cache_name = cmds.getAttr("{}.cacheName".format(cache_node)) or ""
            if cache_path and cache_name:
                base = os.path.join(cache_path, cache_name)
                for ext in (".xml", ".mcx", ".mcc"):
                    candidate = base + ext
                    if os.path.isfile(candidate):
                        os.remove(candidate)
                        files_deleted.append(candidate)

        cmds.delete(cache_node)

        msg = "Deleted cache node '{}'".format(cache_node)
        if files_deleted:
            msg += " and {} file(s)".format(len(files_deleted))

        return skill_success(
            msg,
            prompt="Use list_geometry_caches to confirm deletion.",
            deleted_node=cache_node,
            files_deleted=files_deleted,
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return skill_exception(exc, message="Failed to delete geometry cache")


@skill_entry
def main(**kwargs):
    return delete_geometry_cache(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
