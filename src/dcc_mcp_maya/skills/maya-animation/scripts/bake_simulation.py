"""Bake simulation / constraints to keyframes on objects."""

# Import future modules
from __future__ import annotations

# Import built-in modules
from typing import List, Optional

# Import local modules
from dcc_mcp_core.skill import skill_entry, skill_error, skill_exception, skill_success

from dcc_mcp_maya.api import batch_validate_nodes


def bake_simulation(
    objects: Optional[List[str]] = None,
    start_frame: float = 1.0,
    end_frame: float = 120.0,
    sample_by: float = 1.0,
) -> dict:
    """Bake simulation / constraints to keyframes on objects.

    Converts dynamic simulation or constraint-driven animation into explicit
    keyframes so the objects can be used independently of the rig.

    Args:
        objects: List of object names to bake.  If None, the current selection
            is used.
        start_frame: First frame of the bake range.  Default: 1.
        end_frame: Last frame of the bake range.  Default: 120.
        sample_by: Baking interval in frames (e.g. ``1.0`` = every frame,
            ``0.5`` = every half-frame).  Default: 1.

    Returns:
        ActionResultModel dict with ``context.object_count`` and frame range.
    """
    try:
        import maya.cmds as cmds  # noqa: PLC0415


        targets = objects or []
        if targets:
            err = batch_validate_nodes(cmds, list(targets))
            if err:
                return err
            cmds.select(targets, replace=True)
        else:
            targets = cmds.ls(selection=True) or []

        if not targets:
            return skill_error(
                "No objects to bake",
                "Provide object names or select objects before baking",
            )

        cmds.bakeSimulation(
            targets,
            time=(start_frame, end_frame),
            sampleBy=sample_by,
            simulation=True,
            preserveOutsideKeys=True,
        )
        return skill_success(
            "Baked {} object(s) from frame {} to {}".format(len(targets), start_frame, end_frame),
            object_count=len(targets),
            objects=targets,
            start_frame=start_frame,
            end_frame=end_frame,
            sample_by=sample_by,
            prompt="Use delete_keyframes to trim unwanted frames, or export_animation_curves to save.",
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return skill_exception(exc, message="Failed to bake simulation")


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`bake_simulation`."""
    return bake_simulation(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main
    run_main(main)
