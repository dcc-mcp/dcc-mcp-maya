"""Bake world-space transforms to keyframes over a frame range."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging
from typing import List, Optional

logger = logging.getLogger(__name__)


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
        ActionResultModel dict with ``context.baked_objects`` and the
        ``context.frame_range`` used.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not objects:
            return error_result("No objects provided", "Pass at least one object name.").to_dict()

        missing = [o for o in objects if not cmds.objExists(o)]
        if missing:
            return error_result(
                "Objects not found",
                "Missing: {}".format(", ".join(missing)),
            ).to_dict()

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

        return success_result(
            "Baked transforms for {} object(s) [{} → {}]".format(len(objects), s, e),
            prompt="You can now delete constraints and export the objects. "
            "Use maya-animation skills to further edit keyframes.",
            baked_objects=objects,
            frame_range=[s, e],
            step=step,
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("bake_transforms failed")
        return error_result("Failed to bake transforms", str(exc)).to_dict()


def main(**kwargs):
    return bake_transforms(**kwargs)


if __name__ == "__main__":
    import json

    print(json.dumps(bake_transforms(["pSphere1"], start_frame=1, end_frame=24), indent=2))
