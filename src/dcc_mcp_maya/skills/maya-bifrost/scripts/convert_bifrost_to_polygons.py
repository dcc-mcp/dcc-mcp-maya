"""Bake a Bifrost graph output into a real Maya polygon mesh."""

from __future__ import annotations

from typing import Optional

from dcc_mcp_core.skill import skill_entry

from dcc_mcp_maya.api import maya_error, maya_from_exception, maya_success
from dcc_mcp_maya.bifrost import CONVERT_MODES, BifrostContractError, ensure_bifrost_plugins
from dcc_mcp_maya.bifrost import convert_to_polygons as _convert_to_polygons


def convert_bifrost_to_polygons(
    graph: Optional[str] = None,
    out_mesh: Optional[str] = None,
    name: Optional[str] = None,
    blend: float = 1.0,
    threshold: float = 0.0,
    mode: str = "triangulate",
) -> dict:
    """Convert a Bifrost graph's volumetric output into polygonal geometry."""
    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not graph:
            return maya_error(
                "graph is required",
                "The converter needs the Bifrost graph to read output from.",
                possible_solutions=["Pass graph='bifrostGraphShape1'; use list_bifrost_graphs to find it."],
            )

        runtime = ensure_bifrost_plugins(cmds)
        result = _convert_to_polygons(
            cmds,
            graph=graph,
            out_mesh=out_mesh,
            name=name,
            blend=blend,
            threshold=threshold,
            mode=mode,
        )
        result["runtime"] = runtime
        return maya_success("Converted Bifrost output to {} mesh(es)".format(len(result["meshes"])), **result)
    except BifrostContractError as exc:
        return maya_error(
            "Invalid Bifrost conversion request",
            str(exc),
            possible_solutions=[
                "mode must be one of: " + ", ".join(CONVERT_MODES),
                "The node must be a bifrostGraphShape or bifrostBoard; check list_bifrost_graphs.",
            ],
        )
    except ImportError:
        return maya_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return maya_from_exception(exc, message="Failed to convert Bifrost output to polygons")


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`convert_bifrost_to_polygons`."""
    return convert_bifrost_to_polygons(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
