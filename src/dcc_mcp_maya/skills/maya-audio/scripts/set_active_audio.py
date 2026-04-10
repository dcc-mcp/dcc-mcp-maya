"""Set a sound node as the active timeline audio in Maya."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging

logger = logging.getLogger(__name__)


def set_active_audio(sound_node: str, display_waveform: bool = True) -> dict:
    """Set a sound node as the active audio on Maya's time slider.

    Args:
        sound_node: Name of the sound/audio node to activate.
        display_waveform: If ``True``, enable waveform display on the time slider.

    Returns:
        ActionResultModel dict with ``context.sound_node`` and ``context.display_waveform``.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    if not sound_node:
        return error_result("Invalid sound_node", "sound_node must not be empty").to_dict()

    try:
        import maya.cmds as cmds  # noqa: PLC0415
        import maya.mel as mel  # noqa: PLC0415

        if not cmds.objExists(sound_node):
            return error_result(
                "Sound node not found: '{}'".format(sound_node),
                "Use list_audio_nodes to see available sound nodes.",
            ).to_dict()

        # Use MEL global to access the time slider control
        time_slider = mel.eval("$tmpVar=$gPlayBackSlider")
        cmds.timeControl(
            time_slider,
            edit=True,
            sound=sound_node,
            displaySound=display_waveform,
        )

        return success_result(
            "Set '{}' as active audio".format(sound_node),
            prompt="Audio active. Press play to hear the sound synced to animation.",
            sound_node=sound_node,
            display_waveform=display_waveform,
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("set_active_audio failed")
        return error_result("Failed to set active audio", str(exc)).to_dict()


def main(**kwargs) -> dict:
    return set_active_audio(**kwargs)


if __name__ == "__main__":
    import json

    print(json.dumps(set_active_audio("sound1")))
