"""Set the active timeline audio node."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging

logger = logging.getLogger(__name__)


def set_timeline_audio(sound_node: str) -> dict:
    """Attach a sound node to the Maya timeline for playback.

    After calling this action, playing the timeline in Maya will include
    the audio from the specified sound node.

    Args:
        sound_node: Name of the audio/sound node to attach to the timeline.

    Returns:
        ActionResultModel dict with ``context.sound_node``.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    try:
        import maya.cmds as cmds  # noqa: PLC0415
        import maya.mel as mel  # noqa: PLC0415

        if not cmds.objExists(sound_node):
            return error_result(
                "Sound node not found: {}".format(sound_node),
                "Use import_audio to create a sound node first.",
            ).to_dict()

        node_type = cmds.objectType(sound_node)
        if node_type != "audio":
            return error_result(
                "Not a sound node: {}".format(sound_node),
                "Expected an 'audio' node, got '{}'".format(node_type),
            ).to_dict()

        # Connect to the timeline via the playbackOptions sound attribute
        cmds.timeControl(
            mel.eval("$tmpVar=$gPlayBackSlider"),
            edit=True,
            sound=sound_node,
            displaySound=True,
        )

        return success_result(
            "Set timeline audio to '{}'".format(sound_node),
            prompt="Press play in Maya to hear the audio.",
            sound_node=sound_node,
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("set_timeline_audio failed")
        return error_result("Failed to set timeline audio", str(exc)).to_dict()


def main(**kwargs):
    return set_timeline_audio(**kwargs)


if __name__ == "__main__":
    import json

    result = set_timeline_audio("sound1")
    print(json.dumps(result))
