"""Open a Maya scene file."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import os

# Import local modules
from dcc_mcp_core.skill import skill_entry, skill_error, skill_exception, skill_success


def open_scene(file_path: str, force: bool = False, safe_dirty_check: bool = True) -> dict:
    """Open a Maya scene file.

    Args:
        file_path: Path to the .ma / .mb file.
        force: If True, discard unsaved changes without prompting.
        safe_dirty_check: If True, return a structured error instead of
            allowing Maya to show a save prompt for dirty scenes.

    Returns:
        ToolResult dict.
    """

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not os.path.exists(file_path):
            return skill_error(
                "Scene file does not exist",
                "No file found at {}".format(file_path),
                file_path=file_path,
            )
        if safe_dirty_check and not force and cmds.file(query=True, modified=True):
            return skill_error(
                "Scene has unsaved changes",
                "Refusing to open a scene without force=True because Maya would prompt to save changes.",
                possible_solutions=[
                    "Call save_scene before open_scene.",
                    "Pass force=True to discard unsaved changes.",
                    "Pass safe_dirty_check=False only for an interactive session where a Maya prompt is acceptable.",
                ],
                file_path=file_path,
                scene_modified=True,
            )
        cmds.file(file_path, open=True, force=force)
        return skill_success(
            f"Opened scene: {file_path}",
            file_path=file_path,
            prompt="Use get_scene_info to inspect the scene contents.",
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return skill_exception(exc, message=f"Failed to open {file_path}")


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`open_scene`."""
    return open_scene(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
