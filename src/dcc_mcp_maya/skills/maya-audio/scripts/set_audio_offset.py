"""Set the frame offset for a Maya sound node."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging

logger = logging.getLogger(__name__)


def set_audio_offset(sound_node: str, offset: float) -> dict:
    """Set the playback frame offset for a sound node.

    Args:
        sound_node: Name of the sound/audio node.
        offset: Frame offset — positive values delay audio playback start.

    Returns:
        ActionResultModel dict with ``context.sound_node`` and ``context.offset``.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    if not sound_node:
        return error_result("Invalid sound_node", "sound_node must not be empty").to_dict()

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not cmds.objExists(sound_node):
            return error_result(
                "Sound node not found: '{}'".format(sound_node),
                "Use list_audio_nodes to see available sound nodes.",
            ).to_dict()

        cmds.setAttr("{}.offset".format(sound_node), offset)

        return success_result(
            "Set offset for '{}' to {}".format(sound_node, offset),
            prompt="Offset updated. Play the timeline to verify audio sync.",
            sound_node=sound_node,
            offset=offset,
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("set_audio_offset failed")
        return error_result("Failed to set audio offset", str(exc)).to_dict()


def main(**kwargs) -> dict:
    return set_audio_offset(**kwargs)


if __name__ == "__main__":
    import json

    print(json.dumps(set_audio_offset("sound1", 10.0)))
