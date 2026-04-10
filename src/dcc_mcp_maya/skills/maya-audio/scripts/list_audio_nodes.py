"""List all sound nodes in the Maya scene."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging

logger = logging.getLogger(__name__)


def list_audio_nodes() -> dict:
    """List all sound (audio) nodes in the current Maya scene.

    Returns:
        ActionResultModel dict with ``context.audio_nodes`` (list of dicts)
        and ``context.count``.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        sound_nodes = cmds.ls(type="audio") or []
        items = []
        for node in sound_nodes:
            info = {"node": node}
            try:
                info["file_path"] = cmds.getAttr("{}.filename".format(node)) or ""
                info["offset"] = cmds.getAttr("{}.offset".format(node)) or 0.0
            except Exception:
                info["file_path"] = ""
                info["offset"] = 0.0
            items.append(info)

        return success_result(
            "Found {} audio node(s)".format(len(items)),
            prompt="Use set_active_audio to activate one for timeline display.",
            audio_nodes=items,
            count=len(items),
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("list_audio_nodes failed")
        return error_result("Failed to list audio nodes", str(exc)).to_dict()


def main(**kwargs) -> dict:
    return list_audio_nodes(**kwargs)


if __name__ == "__main__":
    import json

    print(json.dumps(list_audio_nodes()))
