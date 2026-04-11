"""Set the active timeline audio node."""

# Import future modules
from __future__ import annotations

# Import built-in modules
# Import local modules
from dcc_mcp_core.skill import skill_entry, skill_error, skill_exception, skill_success

from dcc_mcp_maya.api import validate_node_exists


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

        err = validate_node_exists(cmds, sound_node)
        if err:
            return err

        node_type = cmds.objectType(sound_node)
        if node_type != "audio":
            return skill_error(
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

        return skill_success(
            "Set timeline audio to '{}'".format(sound_node),
            prompt="Press play in Maya to hear the audio.",
            sound_node=sound_node,
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return skill_exception(exc, message="Failed to set timeline audio")


@skill_entry
def main(**kwargs):
    return set_timeline_audio(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main
    run_main(main)
