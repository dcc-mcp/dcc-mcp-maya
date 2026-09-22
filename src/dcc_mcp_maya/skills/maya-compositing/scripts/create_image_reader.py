"""Create a file node that reads rendered imagery from disk."""

from __future__ import annotations

from typing import Optional

from dcc_mcp_core.skill import skill_entry

from dcc_mcp_maya.api import maya_error, maya_from_exception, maya_success
from dcc_mcp_maya.compositing import CompositingContractError
from dcc_mcp_maya.compositing import create_image_reader as _create_reader


def create_image_reader(
    file_path: Optional[str] = None,
    name: Optional[str] = None,
    use_frame_extension: bool = False,
    frame_offset: int = 0,
    color_space: Optional[str] = None,
) -> dict:
    """Point a new ``file`` node at on-disk imagery."""
    try:
        import maya.cmds as cmds  # noqa: PLC0415

        result = _create_reader(
            cmds,
            file_path=file_path or "",
            name=name,
            use_frame_extension=use_frame_extension,
            frame_offset=frame_offset,
            color_space=color_space,
        )
        return maya_success(
            "Created image reader {} -> {}".format(result["node"], result["file_path"]),
            **result,
        )
    except CompositingContractError as exc:
        return maya_error(
            "Invalid image reader request",
            str(exc),
            possible_solutions=[
                "file_path is required; use the patterns from render_setup.plan_comp_outputs.",
                "Omit color_space on Maya builds without per-file colour management.",
            ],
        )
    except ImportError:
        return maya_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return maya_from_exception(exc, message="Failed to create image reader")


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`create_image_reader`."""
    return create_image_reader(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
