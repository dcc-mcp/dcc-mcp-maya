"""Delete a geometry cache node and optionally its files."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import os

# Import local modules
from dcc_mcp_maya.api import maya_error, maya_from_exception, maya_success


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

        if not cmds.objExists(cache_node):
            return maya_error(
                "Cache node not found: {}".format(cache_node),
                "'{}' does not exist in the scene".format(cache_node),
            )

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

        return maya_success(
            msg,
            prompt="Use list_geometry_caches to confirm deletion.",
            deleted_node=cache_node,
            files_deleted=files_deleted,
        )
    except ImportError:
        return maya_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return maya_from_exception(exc, "Failed to delete geometry cache")


def main(**kwargs):
    return delete_geometry_cache(**kwargs)


if __name__ == "__main__":
    import json

    result = delete_geometry_cache("cacheFile1", delete_files=False)
    print(json.dumps(result))
