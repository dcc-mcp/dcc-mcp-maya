"""Create a polygon sphere."""

# Import future modules
from __future__ import annotations

# Import built-in modules
from typing import Optional

# Import local modules
from dcc_mcp_core.skill import skill_entry, skill_error, skill_exception, skill_success


def create_sphere(radius: float = 1.0, name: Optional[str] = None) -> dict:
    """Create a polygon sphere.

    Args:
        radius: Sphere radius. Default: 1.0.
        name: Optional name for the created object.

    Returns:
        ActionResultModel dict with ``context.object_name``.
    """
    try:
        import maya.cmds as cmds  # noqa: PLC0415

        result = cmds.polySphere(radius=radius, subdivisionsAxis=20, subdivisionsHeight=20)
        obj = result[0]
        if name:
            obj = cmds.rename(obj, name)
        return skill_success(
            f"Created sphere: {obj}",
            object_name=obj,
            radius=radius,
            prompt="Use set_transform to position or assign_material to shade.",
        )
    except ImportError:
        return skill_error(
            "Maya not available",
            "maya.cmds could not be imported",
            possible_solutions=["Run inside Maya or mayapy"],
        )
    except Exception as exc:
        return skill_exception(exc, message="Failed to create sphere")


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`create_sphere`."""
    return create_sphere(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main
    run_main(main)
