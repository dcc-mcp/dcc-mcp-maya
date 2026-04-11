"""Bake geometry deformations to a disk cache file."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import os
from typing import List, Optional

# Import local modules
from dcc_mcp_maya.api import maya_error, maya_from_exception, maya_success


def create_geometry_cache(
    objects: List[str],
    directory: str,
    cache_name: Optional[str] = None,
    start_frame: Optional[float] = None,
    end_frame: Optional[float] = None,
    file_format: str = "mcx",
) -> dict:
    """Bake geometry deformations to a Maya geometry cache.

    Creates ``.xml`` + ``.mcx`` (or ``.mcc``) cache files in the specified
    directory.  The cache records per-vertex positions for each frame.

    Args:
        objects: List of mesh transform names to cache.
        directory: Directory where cache files will be written.
        cache_name: Base name for the cache files.  Defaults to the first
            object name.
        start_frame: First frame to cache.  Defaults to the scene start frame.
        end_frame: Last frame to cache.  Defaults to the scene end frame.
        file_format: Cache file format — ``"mcx"`` (one file per frame,
            default) or ``"mcc"`` (one file for all frames).

    Returns:
        ActionResultModel dict with ``context.cache_files`` and
        ``context.cache_nodes``.
    """
    try:
        import maya.cmds as cmds  # noqa: PLC0415
        import maya.mel as mel  # noqa: PLC0415

        for obj in objects:
            if not cmds.objExists(obj):
                return maya_error(
                    "Object not found: {}".format(obj),
                    "'{}' does not exist in the scene".format(obj),
                )

        if not os.path.isdir(directory):
            os.makedirs(directory)

        sf = start_frame if start_frame is not None else cmds.playbackOptions(query=True, minTime=True)
        ef = end_frame if end_frame is not None else cmds.playbackOptions(query=True, maxTime=True)
        cname = cache_name or objects[0].replace("|", "_").replace(":", "_")

        file_rule = "OneFilePerFrame" if file_format == "mcx" else "OneFile"

        # Use doCreateGeometryCache mel proc (standard Maya cache creation)
        cmds.select(objects)
        mel_cmd = (
            'doCreateGeometryCache 6 {{"0", "{sf}", "{ef}", "{rule}", "0", '
            '"{directory}/", "1", "{cname}", "0", "export", "0", "1", "1", '
            '"0", "1", "mcx"}};'
        ).format(
            sf=int(sf),
            ef=int(ef),
            rule=file_rule,
            directory=directory.replace("\\", "/"),
            cname=cname,
        )
        mel.eval(mel_cmd)

        cache_nodes = cmds.ls(type="cacheFile") or []

        return maya_success(
            "Created geometry cache '{}' ({} — {})".format(cname, int(sf), int(ef)),
            prompt="Use attach_geometry_cache to attach this cache to another mesh, or list_geometry_caches to inspect.",
            cache_name=cname,
            directory=directory,
            start_frame=int(sf),
            end_frame=int(ef),
            cache_nodes=cache_nodes,
        )
    except ImportError:
        return maya_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return maya_from_exception(exc, "Failed to create geometry cache")


def main(**kwargs):
    return create_geometry_cache(**kwargs)


if __name__ == "__main__":
    import json

    result = create_geometry_cache(["pSphere1"], "/tmp/cache", cache_name="sphere_cache")
    print(json.dumps(result))
