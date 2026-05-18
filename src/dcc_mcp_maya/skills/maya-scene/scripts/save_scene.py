"""Save the current Maya scene."""

# Import future modules
from __future__ import annotations

# Import built-in modules
from typing import Optional

# Import local modules
from dcc_mcp_core.skill import skill_entry, skill_error, skill_exception, skill_success

_VALID_FILE_TYPES = {"mayaAscii", "mayaBinary"}


def save_scene(file_path: Optional[str] = None, file_type: str = "mayaBinary") -> dict:
    """Save the current Maya scene.

    Args:
        file_path: Destination path.  If None, saves to the current file path.
        file_type: ``"mayaBinary"`` (default) or ``"mayaAscii"``.

    Returns:
        ToolResult dict.
    """

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if file_type not in _VALID_FILE_TYPES:
            return skill_error("Invalid file_type", "file_type must be mayaAscii or mayaBinary")
        if file_path:
            cmds.file(rename=file_path)
        elif not cmds.file(query=True, sceneName=True):
            return skill_error(
                "Missing file_path",
                "Pass file_path when saving an unnamed scene so Maya does not open a Save As prompt.",
                possible_solutions=[
                    "Pass file_path with a .ma or .mb destination.",
                    "Save the scene interactively once before calling save_scene without file_path.",
                ],
            )
        saved = cmds.file(save=True, type=file_type)
        return skill_success(
            f"Scene saved to {saved}",
            file_path=saved,
            prompt="Use maya_geometry__export_fbx or maya_geometry__export_obj for interchange exports.",
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return skill_exception(exc, message="Failed to save scene")


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`save_scene`."""
    return save_scene(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
