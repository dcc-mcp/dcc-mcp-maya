"""Set translate/rotate/scale on an object."""

# Import future modules
from __future__ import annotations

# Import built-in modules
from typing import List, Optional

# Import local modules
from dcc_mcp_core.skill import skill_entry, skill_error, skill_exception, skill_success

from dcc_mcp_maya.api import validate_node_exists


def _validate_vector3(name: str, value: Optional[List[float]]) -> Optional[dict]:
    if value is None:
        return None
    if not isinstance(value, list) or len(value) != 3:
        return skill_error(
            "Invalid transform vector: {}".format(name),
            "{} must be a list of exactly 3 numeric values".format(name),
            possible_solutions=[
                "Pass {}=[x, y, z].".format(name),
                "Omit {} when you do not want to change it.".format(name),
            ],
            parameter=name,
            value=value,
        )
    try:
        for item in value:
            float(item)
    except (TypeError, ValueError):
        return skill_error(
            "Invalid transform vector: {}".format(name),
            "{} values must be numeric".format(name),
            possible_solutions=[
                "Use ints or floats, for example {}=[1.0, 2.0, 3.0].".format(name),
            ],
            parameter=name,
            value=value,
        )
    return None


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
        ToolResult dict with applied transform values.
    """

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        err = validate_node_exists(cmds, object_name)
        if err:
            return err

        for param_name, value in (
            ("translate", translate),
            ("rotate", rotate),
            ("scale", scale),
        ):
            vector_error = _validate_vector3(param_name, value)
            if vector_error:
                return vector_error

        applied: dict = {}
        if translate is not None:
            cmds.setAttr(f"{object_name}.translate", *translate, type="double3")
            applied["translate"] = translate
        if rotate is not None:
            cmds.setAttr(f"{object_name}.rotate", *rotate, type="double3")
            applied["rotate"] = rotate
        if scale is not None:
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
