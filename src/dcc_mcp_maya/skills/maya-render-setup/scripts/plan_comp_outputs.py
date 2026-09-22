"""Plan per-layer / per-AOV output paths for a compositing hand-off."""

from __future__ import annotations

from typing import List, Optional

from dcc_mcp_core.skill import skill_entry

from dcc_mcp_maya.api import maya_error, maya_from_exception, maya_success
from dcc_mcp_maya.render_setup import RenderSetupContractError
from dcc_mcp_maya.render_setup import build_output_paths as _build


def plan_comp_outputs(
    directory: Optional[str] = None,
    layers: Optional[List[str]] = None,
    aovs: Optional[List[str]] = None,
    file_name: str = "<Scene>",
    start_frame: int = 1,
    end_frame: int = 1,
    frame_padding: int = 4,
    extension: str = "exr",
    separate_aov_folders: bool = True,
    separate_layer_folders: bool = True,
) -> dict:
    """Compose the output paths a comp script will expect.

    This only plans paths - it does not render or export. Feed the result into
    ``maya-shot-export`` or ``maya-render-farm`` to actually produce frames.
    """
    try:
        result = _build(
            directory=directory or "",
            layers=layers,
            aovs=aovs,
            file_name=file_name,
            start_frame=start_frame,
            end_frame=end_frame,
            frame_padding=frame_padding,
            extension=extension,
            separate_aov_folders=separate_aov_folders,
            separate_layer_folders=separate_layer_folders,
        )
        return maya_success(
            "Planned {} output path(s) over frames {}-{}".format(
                result["count"], result["frame_range"][0], result["frame_range"][1]
            ),
            directory=result["directory"],
            outputs=result["outputs"],
            count=result["count"],
            frame_range=result["frame_range"],
            frame_padding=result["frame_padding"],
            extension=result["extension"],
            prompt=("This plans paths only. Use maya-shot-export or maya-render-farm to produce the frames."),
        )
    except RenderSetupContractError as exc:
        return maya_error(
            "Invalid comp output plan",
            str(exc),
            possible_solutions=[
                "directory is required.",
                "frame_padding must be >= 1.",
                "end_frame must be >= start_frame.",
            ],
        )
    except Exception as exc:
        return maya_from_exception(exc, message="Failed to plan comp outputs")


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`plan_comp_outputs`."""
    return plan_comp_outputs(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
