"""Return Maya version, scene path, and basic stats."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging

logger = logging.getLogger(__name__)


def get_session_info() -> dict:
    """Return Maya version, scene path, and basic stats.

    Returns:
        ActionResultModel dict with version, scene, fps information.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        info = {
            "maya_version": cmds.about(version=True),
            "api_version": cmds.about(apiVersion=True),
            "scene_file": cmds.file(query=True, sceneName=True) or "<unsaved>",
            "scene_modified": cmds.file(query=True, modified=True),
            "fps": cmds.currentUnit(query=True, time=True),
            "up_axis": cmds.upAxis(query=True, axis=True),
            "object_count": len(cmds.ls(dag=True) or []),
        }
        return success_result("Maya session info", **info).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("get_session_info failed")
        return error_result("Failed to get session info", str(exc)).to_dict()


def main(**kwargs):
    return get_session_info(**kwargs)


if __name__ == "__main__":
    import json

    result = get_session_info()
    print(json.dumps(result))
