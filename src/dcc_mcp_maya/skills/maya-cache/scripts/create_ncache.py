"""Create an nCache for nCloth or nParticle simulation."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging
from typing import List, Optional

logger = logging.getLogger(__name__)


def create_ncache(
    objects: List[str],
    cache_dir: str,
    cache_name: Optional[str] = None,
    start_frame: Optional[float] = None,
    end_frame: Optional[float] = None,
    one_file_per_frame: bool = False,
) -> dict:
    """Create an nCache for nCloth or nParticle simulation objects.

    Args:
        objects: List of nCloth or nParticle node names to cache.
        cache_dir: Directory to write the cache files into.
        cache_name: Optional base name for the cache files.
        start_frame: Cache start frame (defaults to playback range start).
        end_frame: Cache end frame (defaults to playback range end).
        one_file_per_frame: If ``True``, write one file per frame instead of
            a single multi-frame file.

    Returns:
        ActionResultModel dict with ``context.cache_dir``, ``context.objects``,
        and ``context.frame_range``.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    if not objects:
        return error_result("No objects specified", "Provide nCloth or nParticle nodes.").to_dict()
    if not cache_dir:
        return error_result("No cache_dir specified", "Provide a valid cache directory.").to_dict()

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        missing = [obj for obj in objects if not cmds.objExists(obj)]
        if missing:
            return error_result(
                "Objects not found: {}".format(", ".join(missing)),
                "Use list_nparticle_systems or list_ncloth_nodes to verify node names.",
            ).to_dict()

        sf = start_frame if start_frame is not None else cmds.playbackOptions(query=True, min=True)
        ef = end_frame if end_frame is not None else cmds.playbackOptions(query=True, max=True)

        cache_kwargs = {
            "cacheDirectory": cache_dir,
            "startTime": sf,
            "endTime": ef,
            "singleCache": not one_file_per_frame,
        }
        if cache_name:
            cache_kwargs["fileName"] = cache_name

        # doCreateNclothCache is the standard MEL wrapper; use cmds.cacheFile for direct access
        cmds.select(objects)
        cmds.cacheFile(
            directory=cache_dir,
            startTime=sf,
            endTime=ef,
            singleCache=not one_file_per_frame,
            **({"fileName": cache_name} if cache_name else {}),
        )

        return success_result(
            "Created nCache for {} object(s) in '{}'".format(len(objects), cache_dir),
            prompt="Cache created. Objects will now read from disk on playback.",
            cache_dir=cache_dir,
            objects=objects,
            frame_range=[sf, ef],
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("create_ncache failed")
        return error_result("Failed to create nCache", str(exc)).to_dict()


def main(**kwargs) -> dict:
    return create_ncache(**kwargs)


if __name__ == "__main__":
    import json

    print(json.dumps(create_ncache(["nCloth1"], "/tmp/cache")))
