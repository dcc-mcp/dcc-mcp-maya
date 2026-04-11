"""Export the current selection to a file."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging

logger = logging.getLogger(__name__)


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
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        saved = cmds.file(
            file_path,
            exportSelected=True,
            type=file_type,
            force=True,
        )
        return success_result(
            "Selection exported to {}".format(saved),
            file_path=saved,
            file_type=file_type,
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("export_selection failed")
        return error_result("Failed to export selection", str(exc)).to_dict()


def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`export_selection`."""
    return export_selection(**kwargs)


if __name__ == "__main__":
    import json

    result = export_selection()
    print(json.dumps(result))
