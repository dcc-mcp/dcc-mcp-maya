"""Bake constrained animation to keyframes and remove constraints."""

# Import future modules
from __future__ import annotations

# Import built-in modules
from typing import List, Optional

# Import local modules
from dcc_mcp_maya.api import maya_error, maya_from_exception, maya_success


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
            if not cmds.objExists(obj):
                return maya_error(
                    "Object not found: {}".format(obj),
                    "'{}' does not exist in the scene".format(obj),
                )

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

        return maya_success(
            "Baked {} object(s) from frame {} to {}".format(len(objects), int(sf), int(ef)),
            prompt="Objects are now free with explicit keyframes. Use the Graph Editor to review.",
            baked_objects=objects,
            frame_range=[int(sf), int(ef)],
            constraints_removed=remove_constraints,
        )
    except ImportError:
        return maya_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return maya_from_exception(exc, "Failed to bake constraint")


def main(**kwargs):
    return bake_constraint(**kwargs)


if __name__ == "__main__":
    import json

    result = bake_constraint(["pSphere1"], start_frame=1, end_frame=50)
    print(json.dumps(result))
