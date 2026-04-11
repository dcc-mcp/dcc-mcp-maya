"""Align a list of objects along a given world-space axis."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging
from typing import List, Optional

logger = logging.getLogger(__name__)


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
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    _VALID_AXES = ("x", "y", "z")
    _VALID_MODES = ("min", "center", "max")
    _AXIS_INDEX = {"x": 0, "y": 1, "z": 2}

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not objects or len(objects) < 2:
            return error_result(
                "Insufficient objects",
                "align_objects requires at least 2 objects",
            ).to_dict()

        axis_lower = axis.lower()
        if axis_lower not in _VALID_AXES:
            return error_result(
                "Invalid axis: {}".format(axis),
                "axis must be one of {}".format(_VALID_AXES),
            ).to_dict()

        mode_lower = mode.lower()
        if mode_lower not in _VALID_MODES:
            return error_result(
                "Invalid mode: {}".format(mode),
                "mode must be one of {}".format(_VALID_MODES),
            ).to_dict()

        # Validate all objects exist
        missing = [obj for obj in objects if not cmds.objExists(obj)]
        if missing:
            return error_result(
                "Objects not found: {}".format(missing),
                "The following objects do not exist: {}".format(missing),
            ).to_dict()

        idx = _AXIS_INDEX[axis_lower]

        if reference:
            if not cmds.objExists(reference):
                return error_result(
                    "Reference object not found: {}".format(reference),
                    "'{}' does not exist".format(reference),
                ).to_dict()
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

        return success_result(
            "Aligned {} object(s) along {} axis ({} mode)".format(len(aligned), axis_lower, mode_lower),
            objects=aligned,
            axis=axis_lower,
            mode=mode_lower,
            target_value=target_value,
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("align_objects failed")
        return error_result("Failed to align objects", str(exc)).to_dict()


def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`align_objects`."""
    return align_objects(**kwargs)


if __name__ == "__main__":
    import json

    result = align_objects()
    print(json.dumps(result))
