"""Create a polygon sphere."""

# Import future modules
from __future__ import annotations

# Import built-in modules
from typing import Optional

# Import local modules
from dcc_mcp_core.skill import skill_entry

from dcc_mcp_maya.api import created_object_context, maya_error, maya_from_exception, maya_success


def create_sphere(radius: float = 1.0, name: Optional[str] = None) -> dict:
    """Create a polygon sphere.

    Args:
        radius: Sphere radius. Default: 1.0.
        name: Optional name for the created object.

    Returns:
        ToolResult dict with ``context.object_name``.
    """
    try:
        import maya.cmds as cmds  # noqa: PLC0415

        context = created_object_context(
            cmds,
            cmds.polySphere(radius=radius, subdivisionsAxis=20, subdivisionsHeight=20),
            name,
        )
        context.update(radius=radius)
        return maya_success(
            "Created sphere: {}".format(context["object_name"]),
            prompt="Use set_transform to position or assign_material to shade.",
            **context,
        )
    except ImportError:
        return maya_error(
            "Maya not available",
            "maya.cmds could not be imported",
            possible_solutions=["Run inside Maya or mayapy"],
        )
    except Exception as exc:
        return maya_from_exception(exc, message="Failed to create sphere")


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`create_sphere`."""
    return create_sphere(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
