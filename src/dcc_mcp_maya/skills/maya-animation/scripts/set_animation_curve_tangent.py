"""Set the tangent type on one or all keyframes of an animation curve."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging
from typing import Optional

logger = logging.getLogger(__name__)


def set_animation_curve_tangent(
    object_name: str,
    attribute: str,
    frame: Optional[float] = None,
    tangent_type: str = "auto",
    in_tangent_type: Optional[str] = None,
    out_tangent_type: Optional[str] = None,
) -> dict:
    """Set the tangent type on one or all keyframes of an animation curve.

    Args:
        object_name: Name of the animated object.
        attribute: Attribute name (e.g. ``"tx"``).
        frame: Specific frame to modify.  If None, all keys on the curve
            are updated.
        tangent_type: Tangent preset applied to both in and out tangents.
            One of ``"auto"``, ``"linear"``, ``"flat"``, ``"step"``,
            ``"spline"``, ``"clamped"``, ``"plateau"``.  Default: ``"auto"``.
            Overridden by *in_tangent_type* / *out_tangent_type* if provided.
        in_tangent_type: Override for the incoming tangent type only.
        out_tangent_type: Override for the outgoing tangent type only.

    Returns:
        ActionResultModel dict with ``context.object_name``,
        ``context.attribute``, ``context.frame``, ``context.tangent_type``.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    _VALID_TANGENTS = ("auto", "linear", "flat", "step", "spline", "clamped", "plateau", "stepnext")

    in_type = (in_tangent_type or tangent_type).lower()
    out_type = (out_tangent_type or tangent_type).lower()

    if in_type not in _VALID_TANGENTS:
        return error_result(
            "Invalid in_tangent_type: {}".format(in_type),
            "Must be one of: {}".format(", ".join(_VALID_TANGENTS)),
        ).to_dict()
    if out_type not in _VALID_TANGENTS:
        return error_result(
            "Invalid out_tangent_type: {}".format(out_type),
            "Must be one of: {}".format(", ".join(_VALID_TANGENTS)),
        ).to_dict()

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not cmds.objExists(object_name):
            return error_result(
                "Object not found: {}".format(object_name),
                "'{}' does not exist in the scene".format(object_name),
            ).to_dict()

        plug = "{}.{}".format(object_name, attribute)
        if not cmds.objExists(plug):
            return error_result(
                "Attribute not found: {}".format(plug),
                "'{}.{}' does not exist".format(object_name, attribute),
            ).to_dict()

        kwargs = {
            "attribute": attribute,
            "inTangentType": in_type,
            "outTangentType": out_type,
        }  # type: Dict
        if frame is not None:
            kwargs["time"] = (frame, frame)

        cmds.keyTangent(object_name, edit=True, **kwargs)

        return success_result(
            "Set tangent type on '{}.{}' (frame={})".format(object_name, attribute, frame),
            object_name=object_name,
            attribute=attribute,
            frame=frame,
            in_tangent_type=in_type,
            out_tangent_type=out_type,
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("set_animation_curve_tangent failed")
        return error_result("Failed to set tangent on '{}.{}'".format(object_name, attribute), str(exc)).to_dict()


def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`set_animation_curve_tangent`."""
    return set_animation_curve_tangent(**kwargs)


if __name__ == "__main__":
    import json

    result = set_animation_curve_tangent()
    print(json.dumps(result))
