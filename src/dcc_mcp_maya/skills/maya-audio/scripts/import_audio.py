"""Import an audio file and create a sound node."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import os
from typing import Optional

# Import local modules
from dcc_mcp_core.skill import skill_entry, skill_error, skill_exception, skill_success


def import_audio(
    file_path: str,
    name: Optional[str] = None,
    offset: float = 0.0,
) -> dict:
    """Import an audio file into Maya as a sound node.

    Supports WAV and AIFF formats (Maya limitation).  The created sound node
    can then be assigned to the timeline via ``set_timeline_audio``.

    Args:
        file_path: Absolute path to the audio file.
        name: Optional name for the sound node.
        offset: Frame offset for the audio start.  Default ``0.0``.

    Returns:
        ActionResultModel dict with ``context.sound_node`` and ``context.file_path``.
    """
    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not os.path.isfile(file_path):
            return skill_error(
                "Audio file not found: {}".format(file_path),
                "Ensure the file exists and the path is correct.",
            )

        kwargs = {"file": file_path, "offset": offset}
        if name:
            kwargs["name"] = name

        sound_node = cmds.sound(**kwargs)

        return skill_success(
            "Imported audio '{}'".format(os.path.basename(file_path)),
            prompt="Use set_timeline_audio to attach this sound to the playback timeline.",
            sound_node=sound_node,
            file_path=file_path,
            offset=offset,
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return skill_exception(exc, message="Failed to import audio")


@skill_entry
def main(**kwargs):
    return import_audio(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
