"""Set the Maya project workspace directory."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging
import os

logger = logging.getLogger(__name__)


def set_project(path: str, create_if_missing: bool = False) -> dict:
    """Set the Maya project to the specified directory.

    Creates a workspace.mel if the directory does not already contain one.

    Args:
        path: Absolute path to the project root directory.
        create_if_missing: Create the directory if it does not exist. Default False.

    Returns:
        ActionResultModel dict with ``context.project_path`` and ``context.workspace_mel``.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    if not path:
        return error_result("No project path provided", "Provide 'path' parameter.").to_dict()

    if not os.path.isdir(path):
        if create_if_missing:
            try:
                os.makedirs(path)
            except Exception as exc:
                return error_result("Failed to create directory", str(exc)).to_dict()
        else:
            return error_result(
                "Directory not found",
                "Path '{}' does not exist. Use create_if_missing=True.".format(path),
            ).to_dict()

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        cmds.workspace(path, openWorkspace=True)
        workspace_mel = os.path.join(path, "workspace.mel")
        return success_result(
            "Project set to: {}".format(path),
            prompt="Project set. Use open_scene or publish_asset with paths relative to this project.",
            project_path=path,
            workspace_mel=workspace_mel,
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("set_project failed")
        return error_result("Failed to set Maya project", str(exc)).to_dict()


def main(**kwargs):
    return set_project(**kwargs)


if __name__ == "__main__":
    import json

    result = set_project("/path/to/project")
    print(json.dumps(result))
