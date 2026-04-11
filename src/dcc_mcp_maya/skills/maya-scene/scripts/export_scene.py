"""Export the entire current scene to a file."""

# Import future modules
from __future__ import annotations

# Import local modules
from dcc_mcp_maya.api import maya_error, maya_from_exception, maya_success

# Import built-in modules


def export_scene(file_path: str, file_type: str = "mayaBinary") -> dict:
    """Export the entire current scene to a file.

    Unlike :func:`export_selection` (which exports only selected objects),
    this function exports the complete scene.

    Args:
        file_path: Destination path including file extension.
        file_type: Maya export type string.  Common values:
            ``"mayaBinary"`` (default), ``"mayaAscii"``, ``"FBX export"``.

    Returns:
        ActionResultModel dict with ``context.file_path`` and
        ``context.file_type``.
    """

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        cmds.file(rename=file_path)
        saved = cmds.file(save=True, type=file_type, force=True)
        return maya_success(
            "Scene exported to {}".format(saved),
            file_path=saved,
            file_type=file_type,
            prompt="Check the result with list_scene or use related actions to continue.",
        )
    except ImportError:
        return maya_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return maya_from_exception(exc, "Failed to export scene to '{}'".format(file_path))


def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`export_scene`."""
    return export_scene(**kwargs)


if __name__ == "__main__":
    import json

    result = export_scene()
    print(json.dumps(result))
