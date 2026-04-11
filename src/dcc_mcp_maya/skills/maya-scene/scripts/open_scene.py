"""Open a Maya scene file."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging

logger = logging.getLogger(__name__)


def open_scene(file_path: str, force: bool = False) -> dict:
    """Open a Maya scene file.

    Args:
        file_path: Path to the .ma / .mb file.
        force: If True, discard unsaved changes without prompting.

    Returns:
        ActionResultModel dict.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        cmds.file(file_path, open=True, force=force)
        return success_result(
            f"Opened scene: {file_path}",
            file_path=file_path,
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("open_scene failed")
        return error_result(f"Failed to open {file_path}", str(exc)).to_dict()


def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`open_scene`."""
    return open_scene(**kwargs)


if __name__ == "__main__":
    import json

    result = open_scene()
    print(json.dumps(result))
