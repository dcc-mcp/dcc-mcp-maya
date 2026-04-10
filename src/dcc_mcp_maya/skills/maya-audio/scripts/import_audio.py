"""Import an audio file and create a Maya sound node."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging
from typing import Optional

logger = logging.getLogger(__name__)

SUPPORTED_FORMATS = (".wav", ".aif", ".aiff", ".mp3")


def import_audio(
    file_path: str,
    node_name: Optional[str] = None,
    offset: float = 0.0,
    set_active: bool = False,
) -> dict:
    """Import an audio file and attach it to Maya's timeline.

    Args:
        file_path: Path to the audio file (``.wav``, ``.aif``, ``.mp3``).
        node_name: Optional name for the new sound node.
        offset: Frame offset for audio playback start.
        set_active: If ``True``, set as the active timeline audio immediately.

    Returns:
        ActionResultModel dict with ``context.sound_node`` and ``context.file_path``.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    if not file_path:
        return error_result("No file path specified", "Provide a valid audio file path.").to_dict()

    ext = "." + file_path.rsplit(".", 1)[-1].lower() if "." in file_path else ""
    if ext not in SUPPORTED_FORMATS:
        return error_result(
            "Unsupported audio format '{}'".format(ext),
            "Supported formats: {}".format(", ".join(SUPPORTED_FORMATS)),
        ).to_dict()

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        create_kwargs = {"file": file_path, "offset": offset}
        if node_name:
            create_kwargs["name"] = node_name

        sound_node = cmds.sound(**create_kwargs)

        if set_active:
            cmds.timeControl(
                cmds.melGlobals["$gPlayBackSlider"],
                edit=True,
                sound=sound_node,
                displaySound=True,
            )

        return success_result(
            "Imported audio '{}' as '{}'".format(file_path, sound_node),
            prompt=(
                "Audio imported. Use set_active_audio to enable waveform display, "
                "or set_audio_offset to adjust timing."
            ),
            sound_node=sound_node,
            file_path=file_path,
            offset=offset,
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("import_audio failed")
        return error_result("Failed to import audio", str(exc)).to_dict()


def main(**kwargs) -> dict:
    return import_audio(**kwargs)


if __name__ == "__main__":
    import json

    print(json.dumps(import_audio("/tmp/music.wav")))
