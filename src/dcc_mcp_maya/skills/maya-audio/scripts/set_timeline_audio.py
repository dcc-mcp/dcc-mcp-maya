"""Set the active timeline audio node."""

# Import future modules
from __future__ import annotations

# Import built-in modules
# Import local modules
from dcc_mcp_maya.api import maya_error, maya_from_exception, maya_success


def set_timeline_audio(sound_node: str) -> dict:
    """Attach a sound node to the Maya timeline for playback.

    After calling this action, playing the timeline in Maya will include
    the audio from the specified sound node.

    Args:
        sound_node: Name of the audio/sound node to attach to the timeline.

    Returns:
        ActionResultModel dict with ``context.sound_node``.
    """
    try:
        import maya.cmds as cmds  # noqa: PLC0415
        import maya.mel as mel  # noqa: PLC0415

        if not cmds.objExists(sound_node):
            return maya_error(
                "Sound node not found: {}".format(sound_node),
                "Use import_audio to create a sound node first.",
            )

        node_type = cmds.objectType(sound_node)
        if node_type != "audio":
            return maya_error(
                "Not a sound node: {}".format(sound_node),
                "Expected an 'audio' node, got '{}'".format(node_type),
            )

        # Connect to the timeline via the playbackOptions sound attribute
        cmds.timeControl(
            mel.eval("$tmpVar=$gPlayBackSlider"),
            edit=True,
            sound=sound_node,
            displaySound=True,
        )

        return maya_success(
            "Set timeline audio to '{}'".format(sound_node),
            prompt="Press play in Maya to hear the audio.",
            sound_node=sound_node,
        )
    except ImportError:
        return maya_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return maya_from_exception(exc, "Failed to set timeline audio")


def main(**kwargs):
    return set_timeline_audio(**kwargs)


if __name__ == "__main__":
    import json

    result = set_timeline_audio("sound1")
    print(json.dumps(result))
