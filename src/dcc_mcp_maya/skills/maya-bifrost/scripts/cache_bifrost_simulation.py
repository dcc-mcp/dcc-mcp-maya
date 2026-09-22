"""Attach a geometry cache to a Bifrost graph output for scrubbing and farm renders."""

from __future__ import annotations

from typing import Optional

from dcc_mcp_core.skill import skill_entry

from dcc_mcp_maya.api import maya_error, maya_from_exception, maya_success
from dcc_mcp_maya.bifrost import CACHE_FORMATS, BifrostContractError, ensure_bifrost_plugins
from dcc_mcp_maya.bifrost import write_simulation_cache as _write_simulation_cache


def cache_bifrost_simulation(
    graph: Optional[str] = None,
    directory: Optional[str] = None,
    file_name: Optional[str] = None,
    start_frame: Optional[int] = None,
    end_frame: Optional[int] = None,
    cache_format: str = "OneFile",
) -> dict:
    """Write and attach a geometry cache covering the graph's evaluated output."""
    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not graph:
            return maya_error(
                "graph is required",
                "The cache needs the Bifrost graph whose output should be cached.",
                possible_solutions=["Pass graph='bifrostGraphShape1'; use list_bifrost_graphs to find it."],
            )
        if not directory:
            return maya_error(
                "directory is required",
                "Bifrost caches must be written to an explicit directory.",
                possible_solutions=["Pass directory='<project>/cache/bifrost'."],
            )

        runtime = ensure_bifrost_plugins(cmds)
        result = _write_simulation_cache(
            cmds,
            graph=graph,
            directory=directory,
            file_name=file_name,
            start_frame=start_frame,
            end_frame=end_frame,
            cache_format=cache_format,
        )
        result["runtime"] = runtime
        return maya_success(
            "Cached Bifrost output to {} (frames {} - {})".format(
                result["directory"],
                int(result["frame_range"][0]),
                int(result["frame_range"][1]),
            ),
            **result,
        )
    except BifrostContractError as exc:
        return maya_error(
            "Invalid Bifrost cache request",
            str(exc),
            possible_solutions=[
                "cache_format must be one of: " + ", ".join(CACHE_FORMATS),
                "Omit start_frame / end_frame to use the scene playback range.",
                "The node must be a bifrostGraphShape or bifrostBoard; check list_bifrost_graphs.",
            ],
        )
    except ImportError:
        return maya_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return maya_from_exception(exc, message="Failed to cache Bifrost simulation")


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`cache_bifrost_simulation`."""
    return cache_bifrost_simulation(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
