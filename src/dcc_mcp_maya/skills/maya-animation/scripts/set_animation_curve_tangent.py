"""Set the tangent type on one or all keyframes of an animation curve."""

# Import future modules
from __future__ import annotations

# Import built-in modules
from typing import Optional

# Import local modules
from dcc_mcp_maya.api import maya_error, maya_from_exception, maya_success

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
    _VALID_TANGENTS = ("auto", "linear", "flat", "step", "spline", "clamped", "plateau", "stepnext")

    in_type = (in_tangent_type or tangent_type).lower()
    out_type = (out_tangent_type or tangent_type).lower()

    if in_type not in _VALID_TANGENTS:
        return maya_error(
            "Invalid in_tangent_type: {}".format(in_type),
            "Must be one of: {}".format(", ".join(_VALID_TANGENTS)),
        )
    if out_type not in _VALID_TANGENTS:
        return maya_error(
            "Invalid out_tangent_type: {}".format(out_type),
            "Must be one of: {}".format(", ".join(_VALID_TANGENTS)),
        )

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not cmds.objExists(object_name):
            return maya_error(
                "Object not found: {}".format(object_name),
                "'{}' does not exist in the scene".format(object_name),
            )

        plug = "{}.{}".format(object_name, attribute)
        if not cmds.objExists(plug):
            return maya_error(
                "Attribute not found: {}".format(plug),
                "'{}.{}' does not exist".format(object_name, attribute),
            )

        kwargs = {
            "attribute": attribute,
            "inTangentType": in_type,
            "outTangentType": out_type,
        }  # type: Dict
        if frame is not None:
            kwargs["time"] = (frame, frame)

        cmds.keyTangent(object_name, edit=True, **kwargs)

        return maya_success(
            "Set tangent type on '{}.{}' (frame={})".format(object_name, attribute, frame),
            object_name=object_name,
            attribute=attribute,
            frame=frame,
            in_tangent_type=in_type,
            out_tangent_type=out_type,
        )
    except ImportError:
        return maya_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return maya_from_exception(exc, "Failed to set tangent on '{}.{}'".format(object_name, attribute))

def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`set_animation_curve_tangent`."""
    return set_animation_curve_tangent(**kwargs)

if __name__ == "__main__":
    import json

    result = set_animation_curve_tangent()
    print(json.dumps(result))
