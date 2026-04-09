"""List all animCurve nodes driving an object."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging
from typing import Optional

logger = logging.getLogger(__name__)


def list_animation_curves(
    object_name: str,
    attribute: Optional[str] = None,
) -> dict:
    """List all animCurve nodes driving an object.

    Args:
        object_name: Name of the object to query.
        attribute: Optional specific attribute (e.g. ``"tx"``).  If None,
            all animCurve nodes connected to the object are returned.

    Returns:
        ActionResultModel dict with ``context.curves`` list of dicts
        containing ``name``, ``type``, ``key_count``, and ``attribute``.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not cmds.objExists(object_name):
            return error_result(
                "Object not found: {}".format(object_name),
                "'{}' does not exist in the scene".format(object_name),
            ).to_dict()

        if attribute:
            plug = "{}.{}".format(object_name, attribute)
            raw_conns = cmds.listConnections(plug, source=True, destination=False, type="animCurve") or []
        else:
            raw_conns = cmds.listConnections(object_name, source=True, destination=False, type="animCurve") or []

        # Deduplicate while preserving order
        seen = set()  # type: set
        unique_curves = []  # type: List[str]
        for c in raw_conns:
            if c not in seen:
                seen.add(c)
                unique_curves.append(c)

        curves = []
        for curve in unique_curves:
            curve_type = cmds.objectType(curve)
            key_count = cmds.keyframe(curve, query=True, keyframeCount=True) or 0
            # Determine which attribute this curve drives
            driven_plugs = cmds.listConnections(curve, source=False, destination=True, plugs=True) or []
            driven_attr = driven_plugs[0].split(".")[-1] if driven_plugs else ""
            curves.append(
                {
                    "name": curve,
                    "type": curve_type,
                    "key_count": key_count,
                    "attribute": driven_attr,
                }
            )

        return success_result(
            "Found {} animCurve(s) on '{}'".format(len(curves), object_name),
            object_name=object_name,
            attribute=attribute,
            curves=curves,
            count=len(curves),
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("list_animation_curves failed")
        return error_result("Failed to list animation curves for '{}'".format(object_name), str(exc)).to_dict()


def main(**kwargs):
    return list_animation_curves(**kwargs)


if __name__ == "__main__":
    import json

    result = list_animation_curves()
    print(json.dumps(result))
