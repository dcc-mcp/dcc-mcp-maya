"""Bake world-space transforms to keyframes over a frame range."""

# Import future modules
from __future__ import annotations

# Import built-in modules
from typing import List, Optional

# Import local modules
from dcc_mcp_core.skill import skill_entry, skill_error, skill_exception, skill_success

from dcc_mcp_maya.api import batch_validate_nodes


def bake_transforms(
    objects: List[str],
    start_frame: Optional[float] = None,
    end_frame: Optional[float] = None,
    step: float = 1.0,
    simulate: bool = True,
) -> dict:
    """Bake world-space translate/rotate/scale to keyframes.

    Useful for collapsing constraints or parent hierarchies into raw keyframe
    data before exporting.

    Args:
        objects: List of transform nodes to bake.
        start_frame: Start of bake range.  Defaults to the scene's playback start.
        end_frame: End of bake range.  Defaults to the scene's playback end.
        step: Keyframe interval in frames (default ``1.0``).
        simulate: If ``True``, run dynamics simulation during bake.

    Returns:
        ToolResult dict with ``context.baked_objects`` and the
        ``context.frame_range`` used.
    """

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not objects:
            return skill_error("No objects provided", "Pass at least one object name.")

        err = batch_validate_nodes(cmds, list(objects))
        if err:
            return err

        s = start_frame if start_frame is not None else cmds.playbackOptions(query=True, min=True)
        e = end_frame if end_frame is not None else cmds.playbackOptions(query=True, max=True)

        cmds.bakeResults(
            objects,
            simulation=simulate,
            time=(s, e),
            sampleBy=step,
            attribute=["tx", "ty", "tz", "rx", "ry", "rz", "sx", "sy", "sz"],
            sparseAnimCurveBake=False,
            removeBakedAttributeFromLayer=False,
            bakeOnOverrideLayer=False,
            minimizeRotation=True,
            controlPoints=False,
            shape=True,
        )

        return skill_success(
            "Baked transforms for {} object(s) [{} → {}]".format(len(objects), s, e),
            prompt="You can now delete constraints and export the objects. "
            "Use maya-animation skills to further edit keyframes.",
            baked_objects=objects,
            frame_range=[s, e],
            step=step,
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return skill_exception(exc, message="Failed to bake transforms")


@skill_entry
def main(**kwargs):
    return bake_transforms(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
