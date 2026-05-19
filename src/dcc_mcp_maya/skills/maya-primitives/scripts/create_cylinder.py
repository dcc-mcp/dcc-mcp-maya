"""Create a polygon cylinder."""

# Import future modules
from __future__ import annotations

# Import built-in modules
from typing import Optional

# Import local modules
from dcc_mcp_core.skill import skill_entry

from dcc_mcp_maya.api import created_object_context, maya_error, maya_from_exception, maya_success


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
        ToolResult dict with ``context.object_name``.
    """

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        context = created_object_context(
            cmds, cmds.polyCylinder(radius=radius, height=height, subdivisionsAxis=20), name
        )
        context.update(radius=radius, height=height)
        return maya_success(
            "Created cylinder: {}".format(context["object_name"]),
            prompt="Use set_transform to position or assign_material to shade.",
            **context,
        )
    except ImportError:
        return maya_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return maya_from_exception(exc, message="Failed to create cylinder")


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`create_cylinder`."""
    return create_cylinder(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
