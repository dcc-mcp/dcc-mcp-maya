"""List all animCurve nodes driving an object."""

# Import future modules
from __future__ import annotations

# Import built-in modules
from typing import Optional

# Import local modules
from dcc_mcp_core.skill import skill_entry, skill_error, skill_exception, skill_success


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
    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not cmds.objExists(object_name):
            return skill_error(
                "Object not found: {}".format(object_name),
                "'{}' does not exist in the scene".format(object_name),
            )

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

        return skill_success(
            "Found {} animCurve(s) on '{}'".format(len(curves), object_name),
            object_name=object_name,
            attribute=attribute,
            curves=curves,
            count=len(curves),
            prompt="Use export_animation_curves to save or delete_keyframes to clean up.",
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return skill_exception(exc, message="Failed to list animation curves for '{}'".format(object_name))


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`list_animation_curves`."""
    return list_animation_curves(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main
    run_main(main)
