"""Create a new empty Maya scene."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging

logger = logging.getLogger(__name__)


def new_scene(force: bool = False) -> dict:
    """Create a new Maya scene.

    Args:
        force: If True, discard unsaved changes without prompting.

    Returns:
        ActionResultModel dict.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        cmds.file(new=True, force=force)
        return success_result("New scene created").to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("new_scene failed")
        return error_result("Failed to create new scene", str(exc)).to_dict()


def main(**kwargs):
    return new_scene(**kwargs)


if __name__ == "__main__":
    import json

    result = new_scene()
    print(json.dumps(result))
