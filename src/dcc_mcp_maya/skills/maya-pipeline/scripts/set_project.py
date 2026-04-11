"""Set the Maya project workspace directory."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import os

# Import local modules
from dcc_mcp_core.skill import skill_entry, skill_error, skill_exception, skill_success


def set_project(project_path: str, create_if_missing: bool = False) -> dict:
    """Set the Maya project to the specified directory.

    Creates a workspace.mel if the directory does not already contain one.

    Args:
        project_path: Absolute path to the project root directory.
        create_if_missing: Create the directory if it does not exist. Default False.

    Returns:
        ActionResultModel dict with ``context.project_path`` and ``context.workspace_mel``.
    """

    if not project_path:
        return skill_error("No project path provided", "Provide 'project_path' parameter.")

    if not os.path.isdir(project_path):
        if create_if_missing:
            try:
                os.makedirs(project_path)
            except Exception as exc:
                return skill_error("Failed to create directory", str(exc))
        else:
            return skill_error(
                "Directory not found",
                "Path '{}' does not exist. Use create_if_missing=True.".format(project_path),
            )

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        cmds.workspace(project_path, openWorkspace=True)
        workspace_mel = os.path.join(project_path, "workspace.mel")
        return skill_success(
            "Project set to: {}".format(project_path),
            prompt="Project set. Use open_scene or publish_asset with paths relative to this project.",
            project_path=project_path,
            workspace_mel=workspace_mel,
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return skill_exception(exc, message="Failed to set Maya project")


@skill_entry
def main(**kwargs):
    return set_project(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
