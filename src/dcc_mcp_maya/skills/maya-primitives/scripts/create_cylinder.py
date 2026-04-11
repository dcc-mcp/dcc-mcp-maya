"""Create a polygon cylinder."""

# Import future modules
from __future__ import annotations

# Import built-in modules
from typing import Optional

# Import local modules
from dcc_mcp_core.skill import skill_entry, skill_error, skill_exception, skill_success


def create_cylinder(
    radius: float = 1.0,
    height: float = 2.0,
    name: Optional[str] = None,
) -> dict:
    """Create a polygon cylinder.

    Args:
        radius: Cylinder radius. Default: 1.0.
        height: Cylinder height. Default: 2.0.
        name: Optional name for the created object.

    Returns:
        ActionResultModel dict with ``context.object_name``.
    """

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        result = cmds.polyCylinder(radius=radius, height=height, subdivisionsAxis=20)
        obj = result[0]
        if name:
            obj = cmds.rename(obj, name)
        return skill_success(
            f"Created cylinder: {obj}",
            object_name=obj,
            radius=radius,
            height=height,
            prompt="Use set_transform to position or assign_material to shade.",
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return skill_exception(exc, message="Failed to create cylinder")


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`create_cylinder`."""
    return create_cylinder(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main
    run_main(main)
