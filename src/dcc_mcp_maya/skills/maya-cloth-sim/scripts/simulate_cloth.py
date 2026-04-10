"""Run nCloth simulation over a frame range and optionally cache results."""
from __future__ import annotations

import maya.cmds as cmds
from dcc_mcp_core import error_result, success_result


def run(params: dict) -> object:
    """Simulate nCloth by playing through the timeline.

    Args:
        params: Dictionary with keys:
            - start_frame (float): First frame to simulate. Default timeline start.
            - end_frame (float): Last frame to simulate. Default timeline end.
            - cache (bool): Create nCache after simulation. Default False.
            - cache_dir (str): Directory for cache files. Default temp dir.

    Returns:
        ActionResultModel with simulation result.
    """
    start_frame = params.get("start_frame", None)
    end_frame = params.get("end_frame", None)
    do_cache = params.get("cache", False)
    cache_dir = params.get("cache_dir", "")

    try:
        sf = start_frame if start_frame is not None else cmds.playbackOptions(query=True, minTime=True)
        ef = end_frame if end_frame is not None else cmds.playbackOptions(query=True, maxTime=True)

        # Play through the timeline to simulate
        cmds.currentTime(sf, edit=True)
        for frame in range(int(sf), int(ef) + 1):
            cmds.currentTime(frame, edit=True)

        cloth_nodes = cmds.ls(type="nCloth") or []
        cache_files = []

        if do_cache and cloth_nodes:
            import tempfile
            cd = cache_dir if cache_dir else tempfile.gettempdir()
            for cloth_node in cloth_nodes:
                cache_name = "{0}_cache".format(cloth_node)
                cmds.cacheFile(
                    cnd=cloth_node,
                    directory=cd,
                    fileName=cache_name,
                    format="OneFile",
                    startTime=sf,
                    endTime=ef,
                )
                cache_files.append("{0}/{1}.xml".format(cd, cache_name))

        return success_result(
            "Simulated {0} nCloth node(s) from frame {1} to {2}".format(
                len(cloth_nodes), sf, ef
            ),
            prompt=(
                "Simulation complete. Review the cloth motion and adjust attributes "
                "on the nCloth node if needed."
            ),
            cloth_nodes=cloth_nodes,
            count=len(cloth_nodes),
            start_frame=sf,
            end_frame=ef,
            cache_files=cache_files,
        )
    except Exception as exc:
        return error_result("Failed to simulate cloth", str(exc))
