"""Create a new empty Maya scene."""

# Import future modules
from __future__ import annotations

# Import local modules
from dcc_mcp_core.skill import skill_entry, skill_error, skill_exception, skill_success


def new_scene(force: bool = False, safe_dirty_check: bool = True) -> dict:
    """Create a new Maya scene.

    Args:
        force: If True, discard unsaved changes without prompting.
        safe_dirty_check: If True, return a structured error instead of
            allowing Maya to show a save prompt for dirty scenes.

    Returns:
        ToolResult dict.
    """

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if safe_dirty_check and not force and cmds.file(query=True, modified=True):
            return skill_error(
                "Scene has unsaved changes",
                "Refusing to create a new scene without force=True because Maya would prompt to save changes.",
                possible_solutions=[
                    "Call save_scene before new_scene.",
                    "Pass force=True to discard unsaved changes.",
                    "Pass safe_dirty_check=False only for an interactive session where a Maya prompt is acceptable.",
                ],
                scene_modified=True,
            )
        cmds.file(new=True, force=force)
        return skill_success(
            "New scene created", prompt="Check the result with list_scene or use related actions to continue."
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return skill_exception(exc, message="Failed to create new scene")


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`new_scene`."""
    return new_scene(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
