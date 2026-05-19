"""Create a polygon cube."""

# Import future modules
from __future__ import annotations

# Import built-in modules
from typing import Optional

# Import local modules
from dcc_mcp_core.skill import skill_entry

from dcc_mcp_maya.api import created_object_context, maya_error, maya_from_exception, maya_success


def create_cube(
    width: float = 1.0,
    height: float = 1.0,
    depth: float = 1.0,
    name: Optional[str] = None,
) -> dict:
    """Create a polygon cube.

    Args:
        width: Cube width. Default: 1.0.
        height: Cube height. Default: 1.0.
        depth: Cube depth. Default: 1.0.
        name: Optional name for the created object.

    Returns:
        ToolResult dict with ``context.object_name``.
    """

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        context = created_object_context(cmds, cmds.polyCube(width=width, height=height, depth=depth), name)
        context.update(width=width, height=height, depth=depth)
        return maya_success(
            "Created cube: {}".format(context["object_name"]),
            prompt="Use set_transform to position or assign_material to shade.",
            **context,
        )
    except ImportError:
        return maya_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return maya_from_exception(exc, message="Failed to create cube")


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`create_cube`."""
    return create_cube(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
