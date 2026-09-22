"""Write Maya geometry / nCache files for Nucleus or deformable output."""

from __future__ import annotations

from typing import List, Optional

from dcc_mcp_core.skill import skill_entry

from dcc_mcp_maya import check_maya_cancelled
from dcc_mcp_maya.api import maya_error, maya_from_exception, maya_success
from dcc_mcp_maya.nucleus import (
    CACHE_DATA_FORMATS,
    CACHE_FORMATS,
    NucleusContractError,
)
from dcc_mcp_maya.nucleus import write_cache as _write_cache


def create_ncache(
    objects: Optional[List[str]] = None,
    directory: Optional[str] = None,
    file_name: Optional[str] = None,
    start_frame: Optional[int] = None,
    end_frame: Optional[int] = None,
    cache_format: str = "OneFile",
    data_format: str = "mcc",
    world_space: bool = False,
) -> dict:
    """Write one cache file per node over the requested frame range."""
    try:
        import maya.cmds as cmds  # noqa: PLC0415

        targets = objects or [str(item) for item in (cmds.ls(selection=True) or [])]
        if not targets:
            return maya_error(
                "No objects selected for caching",
                "Provide objects or select the nodes whose output should be cached.",
                possible_solutions=["Pass objects=['nClothShape1'] or select the simulated meshes."],
            )
        if not directory:
            return maya_error(
                "directory is required",
                "nCache files must be written to an explicit directory.",
                possible_solutions=["Pass directory='<project>/cache/nCloth'."],
            )

        result = _write_cache(
            cmds,
            nodes=targets,
            directory=directory,
            file_name=file_name,
            start_frame=start_frame,
            end_frame=end_frame,
            cache_format=cache_format,
            data_format=data_format,
            world_space=world_space,
            on_cancelled=check_maya_cancelled,
        )
        return maya_success(
            "Wrote {} cache(s) for frames {} - {}".format(
                result["count"],
                int(result["frame_range"][0]),
                int(result["frame_range"][1]),
            ),
            caches=result["caches"],
            count=result["count"],
            frame_range=result["frame_range"],
            directory=directory,
            prompt="Detach or remove these caches later with delete_ncache.",
        )
    except NucleusContractError as exc:
        return maya_error(
            "Invalid cache request",
            str(exc),
            possible_solutions=[
                "cache_format must be one of: " + ", ".join(CACHE_FORMATS),
                "data_format must be one of: " + ", ".join(CACHE_DATA_FORMATS),
                "Only nCloth, mesh, nurbsSurface and nurbsCurve output can be cached.",
            ],
        )
    except ImportError:
        return maya_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return maya_from_exception(exc, message="Failed to write nCache")


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`create_ncache`."""
    return create_ncache(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
