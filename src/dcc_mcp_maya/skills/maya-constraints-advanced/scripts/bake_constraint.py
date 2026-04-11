"""Bake constrained animation to keyframes and remove constraints."""

# Import future modules
from __future__ import annotations

# Import built-in modules
from typing import List, Optional

# Import local modules
from dcc_mcp_core.skill import skill_entry, skill_error, skill_exception, skill_success

from dcc_mcp_maya.api import validate_node_exists


def bake_constraint(
    objects: List[str],
    start_frame: Optional[float] = None,
    end_frame: Optional[float] = None,
    sample_by: float = 1.0,
    remove_constraints: bool = True,
) -> dict:
    """Bake constrained animation to keyframes.

    Samples the transform values of each object on every frame (or every
    ``sample_by`` frames) and creates explicit keyframes.  Optionally deletes
    the driving constraints after baking so the objects become free.

    Args:
        objects: List of transform names to bake.
        start_frame: First frame to bake.  Defaults to scene playback start.
        end_frame: Last frame to bake.  Defaults to scene playback end.
        sample_by: Bake every N frames.  Default ``1.0`` (every frame).
        remove_constraints: If ``True`` (default), delete all constraints on
            the objects after baking.

    Returns:
        ActionResultModel dict with ``context.baked_objects`` and
        ``context.frame_range``.
    """
    try:
        import maya.cmds as cmds  # noqa: PLC0415

        for obj in objects:
            err = validate_node_exists(cmds, obj)
            if err:
                return err

        sf = start_frame if start_frame is not None else cmds.playbackOptions(query=True, minTime=True)
        ef = end_frame if end_frame is not None else cmds.playbackOptions(query=True, maxTime=True)

        cmds.bakeResults(
            objects,
            time=(sf, ef),
            sampleBy=sample_by,
            simulation=True,
            disableImplicitControl=True,
            preserveOutsideKeys=True,
            controlPoints=False,
            shape=False,
        )

        if remove_constraints:
            for obj in objects:
                constraints = cmds.listRelatives(obj, type="constraint") or []
                constraints += cmds.listConnections(obj, type="constraint") or []
                for con in set(constraints):
                    if cmds.objExists(con):
                        cmds.delete(con)

        return skill_success(
            "Baked {} object(s) from frame {} to {}".format(len(objects), int(sf), int(ef)),
            prompt="Objects are now free with explicit keyframes. Use the Graph Editor to review.",
            baked_objects=objects,
            frame_range=[int(sf), int(ef)],
            constraints_removed=remove_constraints,
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return skill_exception(exc, message="Failed to bake constraint")


@skill_entry
def main(**kwargs):
    return bake_constraint(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main
    run_main(main)
