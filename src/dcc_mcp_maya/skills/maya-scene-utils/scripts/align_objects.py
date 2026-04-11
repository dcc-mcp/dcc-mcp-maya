"""Align a list of objects along a given world-space axis."""

# Import future modules
from __future__ import annotations

# Import built-in modules
from typing import List, Optional

# Import local modules
from dcc_mcp_core.skill import skill_entry, skill_error, skill_exception, skill_success

from dcc_mcp_maya.api import validate_node_exists


def align_objects(
    objects: List[str],
    axis: str = "x",
    mode: str = "center",
    reference: Optional[str] = None,
) -> dict:
    """Align a list of objects along a given world-space axis.

    Each object's translate component along *axis* is set so that its
    bounding-box minimum, center, or maximum coincides with the reference
    value.  By default the reference value is derived from the bounding box
    of all provided objects combined; alternatively a specific *reference*
    object can be specified.

    Args:
        objects: List of object names to align (minimum 2).
        axis: World-space axis to align along — ``"x"``, ``"y"``, or ``"z"``.
            Default: ``"x"``.
        mode: Alignment mode — ``"min"`` (align left/bottom/front edges),
            ``"center"`` (align centres, default), or ``"max"`` (align
            right/top/back edges).
        reference: Optional name of a reference object whose bounding-box
            value on *axis* is used as the target.  If None, the combined
            bounding box of all *objects* is used.

    Returns:
        ActionResultModel dict with ``context.objects``, ``context.axis``,
        ``context.mode``, ``context.target_value``.
    """

    _VALID_AXES = ("x", "y", "z")
    _VALID_MODES = ("min", "center", "max")
    _AXIS_INDEX = {"x": 0, "y": 1, "z": 2}

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not objects or len(objects) < 2:
            return skill_error(
                "Insufficient objects",
                "align_objects requires at least 2 objects",
            )

        axis_lower = axis.lower()
        if axis_lower not in _VALID_AXES:
            return skill_error(
                "Invalid axis: {}".format(axis),
                "axis must be one of {}".format(_VALID_AXES),
            )

        mode_lower = mode.lower()
        if mode_lower not in _VALID_MODES:
            return skill_error(
                "Invalid mode: {}".format(mode),
                "mode must be one of {}".format(_VALID_MODES),
            )

        # Validate all objects exist
        missing = [obj for obj in objects if not cmds.objExists(obj)]
        if missing:
            return skill_error(
                "Objects not found: {}".format(missing),
                "The following objects do not exist: {}".format(missing),
            )

        idx = _AXIS_INDEX[axis_lower]

        if reference:
            err = validate_node_exists(cmds, reference)
            if err:
                return err
            ref_bb = cmds.exactWorldBoundingBox(reference)
            # bb = [xmin, ymin, zmin, xmax, ymax, zmax]
            if mode_lower == "min":
                target_value = ref_bb[idx]
            elif mode_lower == "max":
                target_value = ref_bb[idx + 3]
            else:
                target_value = (ref_bb[idx] + ref_bb[idx + 3]) / 2.0
        else:
            # Combined bounding box
            all_bb = [cmds.exactWorldBoundingBox(obj) for obj in objects]
            combined_min = min(bb[idx] for bb in all_bb)
            combined_max = max(bb[idx + 3] for bb in all_bb)
            if mode_lower == "min":
                target_value = combined_min
            elif mode_lower == "max":
                target_value = combined_max
            else:
                target_value = (combined_min + combined_max) / 2.0

        translate_attr = {"x": "tx", "y": "ty", "z": "tz"}[axis_lower]
        aligned = []
        for obj in objects:
            bb = cmds.exactWorldBoundingBox(obj)
            obj_min = bb[idx]
            obj_max = bb[idx + 3]
            if mode_lower == "min":
                obj_ref = obj_min
            elif mode_lower == "max":
                obj_ref = obj_max
            else:
                obj_ref = (obj_min + obj_max) / 2.0

            current_t = cmds.getAttr("{}.{}".format(obj, translate_attr))
            delta = target_value - obj_ref
            cmds.setAttr("{}.{}".format(obj, translate_attr), current_t + delta)
            aligned.append(obj)

        return skill_success(
            "Aligned {} object(s) along {} axis ({} mode)".format(len(aligned), axis_lower, mode_lower),
            objects=aligned,
            axis=axis_lower,
            mode=mode_lower,
            target_value=target_value,
            prompt="Check the result with list_scene_utils or use related actions to continue.",
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return skill_exception(exc, message="Failed to align objects")


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`align_objects`."""
    return align_objects(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main
    run_main(main)
