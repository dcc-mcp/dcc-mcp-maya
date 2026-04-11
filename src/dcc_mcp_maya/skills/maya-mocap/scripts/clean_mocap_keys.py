"""Simplify and clean up dense mocap keyframe curves."""

# Import future modules
from __future__ import annotations

# Import built-in modules
from typing import List, Optional

# Import local modules
from dcc_mcp_maya.api import maya_error, maya_from_exception, maya_success


def clean_mocap_keys(
    joints: Optional[List[str]] = None,
    time_tolerance: float = 0.05,
    value_tolerance: float = 0.01,
    start_frame: Optional[int] = None,
    end_frame: Optional[int] = None,
) -> dict:
    """Reduce keyframe density on mocap joints using Maya simplify curves.

    Args:
        joints: List of joint names to clean. If empty, all scene joints are processed.
        time_tolerance: Time simplification tolerance. Default ``0.05``.
        value_tolerance: Value simplification tolerance. Default ``0.01``.
        start_frame: Start of range to simplify. Optional.
        end_frame: End of range to simplify. Optional.

    Returns:
        ActionResultModel dict with ``context.keys_before``, ``context.keys_after``,
        and ``context.keys_removed``.
    """

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if joints:
            targets = [j for j in joints if cmds.objExists(j)]
        else:
            targets = cmds.ls(type="joint") or []

        if not targets:
            return maya_error(
                "No joints found to clean",
                "Specify joint names or ensure joints exist in the scene.",
            )

        anim_curves_before = cmds.keyframe(targets, query=True, keyframeCount=True) or 0

        simplify_kwargs = {
            "timeTolerance": time_tolerance,
            "valueTolerance": value_tolerance,
            "floatTolerance": value_tolerance,
        }
        if start_frame is not None and end_frame is not None:
            simplify_kwargs["time"] = (start_frame, end_frame)

        cmds.select(targets, replace=True)
        cmds.simplify(**simplify_kwargs)

        anim_curves_after = cmds.keyframe(targets, query=True, keyframeCount=True) or 0
        removed = anim_curves_before - anim_curves_after

        return maya_success(
            "Cleaned {} joint(s): {} -> {} keys (removed {})".format(
                len(targets), anim_curves_before, anim_curves_after, removed
            ),
            prompt="Keyframes simplified. Review the motion in the Graph Editor.",
            joints_processed=len(targets),
            keys_before=anim_curves_before,
            keys_after=anim_curves_after,
            keys_removed=removed,
        )
    except ImportError:
        return maya_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return maya_from_exception(exc, "Failed to clean mocap keys")


def main(**kwargs):
    return clean_mocap_keys(**kwargs)


if __name__ == "__main__":
    import json

    result = clean_mocap_keys()
    print(json.dumps(result))
