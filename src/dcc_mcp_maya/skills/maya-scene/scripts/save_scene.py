"""Save the current Maya scene."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging
from typing import Optional

logger = logging.getLogger(__name__)


def save_scene(file_path: Optional[str] = None, file_type: str = "mayaBinary") -> dict:
    """Save the current Maya scene.

    Args:
        file_path: Destination path.  If None, saves to the current file path.
        file_type: ``"mayaBinary"`` (default) or ``"mayaAscii"``.

    Returns:
        ActionResultModel dict.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if file_path:
            cmds.file(rename=file_path)
        saved = cmds.file(save=True, type=file_type)
        return success_result(
            f"Scene saved to {saved}",
            file_path=saved,
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("save_scene failed")
        return error_result("Failed to save scene", str(exc)).to_dict()


def main(**kwargs):
    return save_scene(**kwargs)


if __name__ == "__main__":
    import json

    result = save_scene()
    print(json.dumps(result))
