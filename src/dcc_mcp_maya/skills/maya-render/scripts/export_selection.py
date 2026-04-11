"""Export the current selection to a file."""

# Import future modules
from __future__ import annotations

# Import local modules
from dcc_mcp_maya.api import maya_error, maya_from_exception, maya_success

def export_selection(
    file_path: str,
    file_type: str = "FBX export",
) -> dict:
    """Export the current selection to a file.

    Args:
        file_path: Destination file path.
        file_type: Export format string as understood by ``cmds.file(type=...)``.
            Common values: ``"FBX export"``, ``"OBJexport"``, ``"mayaBinary"``,
            ``"mayaAscii"``, ``"Alembic"``.  Default: ``"FBX export"``.

    Returns:
        ActionResultModel dict.
    """

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        saved = cmds.file(
            file_path,
            exportSelected=True,
            type=file_type,
            force=True,
        )
        return maya_success(
            "Selection exported to {}".format(saved),
            file_path=saved,
            file_type=file_type,
        )
    except ImportError:
        return maya_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return maya_from_exception(exc, "Failed to export selection")

def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`export_selection`."""
    return export_selection(**kwargs)

if __name__ == "__main__":
    import json

    result = export_selection()
    print(json.dumps(result))
