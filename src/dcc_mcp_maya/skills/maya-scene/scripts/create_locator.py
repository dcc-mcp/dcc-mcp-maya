"""Create a Maya locator node."""

# Import future modules
from __future__ import annotations

# Import built-in modules
from typing import List, Optional

# Import local modules
from dcc_mcp_core.skill import skill_entry, skill_error, skill_exception, skill_success


def create_locator(name: Optional[str] = None, position: Optional[List[float]] = None) -> dict:
    """Create a Maya locator node.

    Locators are non-renderable helper nodes commonly used as position markers,
    aim targets, or constraint targets.

    Args:
        name: Optional name for the locator's transform node.  If None, Maya
            generates a default name (``"locator1"``, etc.).
        position: Optional ``[x, y, z]`` world-space position.  If None, the
            locator is created at the origin.

    Returns:
        ActionResultModel dict with ``context.object_name`` and
        ``context.position``.
    """

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        result = cmds.spaceLocator(name=name) if name else cmds.spaceLocator()
        loc_transform = result[0]

        if position and len(position) == 3:
            cmds.move(position[0], position[1], position[2], loc_transform)

        pos = position or [0.0, 0.0, 0.0]
        return skill_success(
            "Created locator '{}'".format(loc_transform),
            object_name=loc_transform,
            position=pos,
            prompt="Check the result with list_scene or use related actions to continue.",
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return skill_exception(exc, message="Failed to create locator")


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`create_locator`."""
    return create_locator(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main
    run_main(main)
