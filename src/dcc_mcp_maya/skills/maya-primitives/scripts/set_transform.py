"""Set translate/rotate/scale on an object."""

# Import future modules
from __future__ import annotations

# Import built-in modules
from typing import List, Optional

# Import local modules
from dcc_mcp_maya.api import maya_error, maya_from_exception, maya_success

def set_transform(
    object_name: str,
    translate: Optional[List[float]] = None,
    rotate: Optional[List[float]] = None,
    scale: Optional[List[float]] = None,
) -> dict:
    """Set the translate/rotate/scale of an object.

    Args:
        object_name: Name of the object to transform.
        translate: [tx, ty, tz] in scene units.  None = no change.
        rotate: [rx, ry, rz] in degrees.  None = no change.
        scale: [sx, sy, sz].  None = no change.

    Returns:
        ActionResultModel dict with applied transform values.
    """

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not cmds.objExists(object_name):
            return maya_error(
                f"Object not found: {object_name}",
                f"'{object_name}' does not exist in the scene",
            )

        applied: dict = {}
        if translate is not None and len(translate) == 3:
            cmds.setAttr(f"{object_name}.translate", *translate, type="double3")
            applied["translate"] = translate
        if rotate is not None and len(rotate) == 3:
            cmds.setAttr(f"{object_name}.rotate", *rotate, type="double3")
            applied["rotate"] = rotate
        if scale is not None and len(scale) == 3:
            cmds.setAttr(f"{object_name}.scale", *scale, type="double3")
            applied["scale"] = scale

        return maya_success(
            f"Transform applied to {object_name}",
            object_name=object_name,
            **applied,
        )
    except ImportError:
        return maya_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return maya_from_exception(exc, f"Failed to set transform on {object_name}")

def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`set_transform`."""
    return set_transform(**kwargs)

if __name__ == "__main__":
    import json

    result = set_transform()
    print(json.dumps(result))
