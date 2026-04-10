"""List all sound nodes in the Maya scene."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging

logger = logging.getLogger(__name__)


def list_audio() -> dict:
    """List all sound nodes in the current Maya scene.

    Returns:
        ActionResultModel dict with ``context.sound_nodes`` (list of dicts
        with ``node``, ``file_path``, ``offset``) and ``context.count``.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        sound_nodes = cmds.ls(type="audio") or []
        result = []
        for node in sound_nodes:
            file_path = cmds.getAttr("{}.filename".format(node)) or ""
            offset = cmds.getAttr("{}.offset".format(node)) or 0.0
            result.append(
                {
                    "node": node,
                    "file_path": file_path,
                    "offset": offset,
                }
            )

        return success_result(
            "Found {} sound node(s)".format(len(result)),
            prompt="Use set_timeline_audio to activate a sound, or remove_audio to delete one.",
            sound_nodes=result,
            count=len(result),
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("list_audio failed")
        return error_result("Failed to list audio nodes", str(exc)).to_dict()


def main(**kwargs):
    return list_audio(**kwargs)


if __name__ == "__main__":
    import json

    result = list_audio()
    print(json.dumps(result))
