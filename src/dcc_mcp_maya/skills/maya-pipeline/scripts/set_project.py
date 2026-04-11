"""Set the Maya project workspace directory."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import os


# Import local modules
from dcc_mcp_maya.api import maya_error, maya_from_exception, maya_success


def set_project(path: str, create_if_missing: bool = False) -> dict:
    """Set the Maya project to the specified directory.

    Creates a workspace.mel if the directory does not already contain one.

    Args:
        path: Absolute path to the project root directory.
        create_if_missing: Create the directory if it does not exist. Default False.

    Returns:
        ActionResultModel dict with ``context.project_path`` and ``context.workspace_mel``.
    """

    if not path:
        return maya_error("No project path provided", "Provide 'path' parameter.")

    if not os.path.isdir(path):
        if create_if_missing:
            try:
                os.makedirs(path)
            except Exception as exc:
                return maya_error("Failed to create directory", str(exc))
        else:
            return maya_error(
                "Directory not found",
                "Path '{}' does not exist. Use create_if_missing=True.".format(path),
            )

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        cmds.workspace(path, openWorkspace=True)
        workspace_mel = os.path.join(path, "workspace.mel")
        return maya_success(
            "Project set to: {}".format(path),
            prompt="Project set. Use open_scene or publish_asset with paths relative to this project.",
            project_path=path,
            workspace_mel=workspace_mel,
        )
    except ImportError:
        return maya_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return maya_from_exception(exc, "Failed to set Maya project")


def main(**kwargs):
    return set_project(**kwargs)


if __name__ == "__main__":
    import json

    result = set_project("/path/to/project")
    print(json.dumps(result))
