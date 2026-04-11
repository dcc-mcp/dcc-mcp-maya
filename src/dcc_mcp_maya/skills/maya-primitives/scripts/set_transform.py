"""Set translate/rotate/scale on an object."""

# Import future modules
from __future__ import annotations

# Import built-in modules
from typing import List, Optional

# Import local modules
from dcc_mcp_core.skill import skill_entry, skill_error, skill_exception, skill_success

from dcc_mcp_maya.api import validate_node_exists


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

        err = validate_node_exists(cmds, object_name)
        if err:
            return err

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

        return skill_success(
            f"Transform applied to {object_name}",
            object_name=object_name,
            **applied,
            prompt="Check the result with list_primitives or use related actions to continue.",
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return skill_exception(exc, message=f"Failed to set transform on {object_name}")


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`set_transform`."""
    return set_transform(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
