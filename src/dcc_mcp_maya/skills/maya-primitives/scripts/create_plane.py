"""Create a polygon plane."""

# Import future modules
from __future__ import annotations

# Import built-in modules
from typing import Optional

# Import local modules
from dcc_mcp_core.skill import skill_entry, skill_error, skill_exception, skill_success


def create_plane(
    width: float = 1.0,
    height: float = 1.0,
    name: Optional[str] = None,
) -> dict:
    """Create a polygon plane.

    Args:
        width: Plane width. Default: 1.0.
        height: Plane height. Default: 1.0.
        name: Optional name for the created object.

    Returns:
        ActionResultModel dict with ``context.object_name``.
    """

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        result = cmds.polyPlane(width=width, height=height, subdivisionsX=1, subdivisionsY=1)
        obj = result[0]
        if name:
            obj = cmds.rename(obj, name)
        return skill_success(
            "Created plane: {}".format(obj),
            object_name=obj,
            width=width,
            height=height,
            prompt="Use set_transform to position or assign_material to shade.",
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return skill_exception(exc, message="Failed to create plane")


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`create_plane`."""
    return create_plane(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main
    run_main(main)
