"""Export the entire current scene to a file."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging

logger = logging.getLogger(__name__)


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
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        cmds.file(rename=file_path)
        saved = cmds.file(save=True, type=file_type, force=True)
        return success_result(
            "Scene exported to {}".format(saved),
            file_path=saved,
            file_type=file_type,
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("export_scene failed")
        return error_result("Failed to export scene to '{}'".format(file_path), str(exc)).to_dict()


def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`export_scene`."""
    return export_scene(**kwargs)


if __name__ == "__main__":
    import json

    result = export_scene()
    print(json.dumps(result))
