"""Create a sculpt deformer on one or more objects."""

# Import future modules
from __future__ import annotations

# Import built-in modules
from typing import List, Optional

# Import local modules
from dcc_mcp_maya.api import maya_error, maya_from_exception, maya_success


def sculpt_deformer(
    objects: List[str],
    name: Optional[str] = None,
    mode: str = "stretch",
    max_displacement: float = 1.0,
) -> dict:
    """Create a sculpt deformer on one or more objects.

    The sculpt deformer displaces vertices based on a sculpt sphere that can
    stretch, project, or flip the surface geometry.

    Args:
        objects: List of mesh names to deform.
        name: Optional base name for the sculpt/sphere nodes.
        mode: Deformation mode — ``"stretch"`` (0), ``"project"`` (1), or
            ``"flip"`` (2).  Default: ``"stretch"``.
        max_displacement: Maximum vertex displacement amount.  Default: ``1.0``.

    Returns:
        ActionResultModel dict with ``context.sculpt_node``,
        ``context.sculpt_sphere``, ``context.sculpt_origin``.
    """
    mode_map = {"stretch": 0, "project": 1, "flip": 2}
    mode_lower = mode.lower()
    if mode_lower not in mode_map:
        return maya_error(
            "Invalid mode: {}".format(mode),
            "Valid modes: {}".format(", ".join(mode_map.keys())),
        )

    if not objects:
        return maya_error(
            "No objects specified",
            "Provide at least one mesh name in 'objects'",
        )

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        missing = [o for o in objects if not cmds.objExists(o)]
        if missing:
            return maya_error(
                "Object(s) not found: {}".format(", ".join(missing)),
                "Ensure all objects exist in the scene",
            )

        sculpt_kwargs = {
            "mode": mode_map[mode_lower],
            "maxDisplacement": max_displacement,
        }
        if name:
            sculpt_kwargs["name"] = name

        result = cmds.sculpt(objects, **sculpt_kwargs)
        # cmds.sculpt returns [sculptNode, sculptSphere, sculptOrigin]
        sculpt_node = result[0] if result else None
        sculpt_sphere = result[1] if result and len(result) > 1 else None
        sculpt_origin = result[2] if result and len(result) > 2 else None

        return maya_success(
            "Created sculpt deformer '{}' (mode='{}') on {} object(s)".format(sculpt_node, mode_lower, len(objects)),
            sculpt_node=sculpt_node,
            sculpt_sphere=sculpt_sphere,
            sculpt_origin=sculpt_origin,
            objects=list(objects),
            mode=mode_lower,
            max_displacement=max_displacement,
        )
    except ImportError:
        return maya_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return maya_from_exception(exc, "Failed to create sculpt deformer")


def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`sculpt_deformer`."""
    return sculpt_deformer(**kwargs)


if __name__ == "__main__":
    import json

    result = sculpt_deformer()
    print(json.dumps(result))
