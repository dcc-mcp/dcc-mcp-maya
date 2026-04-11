"""Save the current Maya export settings as a JSON preset file."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import json
import os
from typing import Dict, List, Optional

# Import local modules
from dcc_mcp_core.skill import skill_entry, skill_error, skill_exception, skill_success


def save_export_preset(
    preset_name: str,
    preset_dir: Optional[str] = None,
    format: str = "fbx",
    frame_range: Optional[List[int]] = None,
    custom_settings: Optional[Dict[str, object]] = None,
) -> dict:
    """Save export configuration to a JSON preset file.

    Args:
        preset_name: Name for the preset (used as filename stem).
        preset_dir: Directory to save the preset. Defaults to
            ``<project_root>/export_presets``.
        format: Export format hint: ``'fbx'``, ``'alembic'``, or ``'obj'``.
            Default ``'fbx'``.
        frame_range: ``[start, end]`` frame range. Defaults to current timeline.
        custom_settings: Optional additional key-value pairs to store.

    Returns:
        ActionResultModel dict with ``context.preset_path`` and
        ``context.preset_data``.
    """
    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not preset_dir:
            project = cmds.workspace(query=True, rootDirectory=True)
            preset_dir = os.path.join(project, "export_presets")

        if not os.path.isdir(preset_dir):
            os.makedirs(preset_dir)

        if frame_range is None:
            frame_range = [
                int(cmds.playbackOptions(query=True, minTime=True)),
                int(cmds.playbackOptions(query=True, maxTime=True)),
            ]

        scene_file = cmds.file(query=True, sceneName=True) or ""
        fps = cmds.currentUnit(query=True, time=True)

        preset_data = {
            "preset_name": preset_name,
            "format": format,
            "frame_range": frame_range,
            "fps": fps,
            "scene_file": scene_file,
        }
        if custom_settings:
            preset_data.update(custom_settings)

        preset_path = os.path.join(preset_dir, "{}.json".format(preset_name))
        with open(preset_path, "w") as fh:
            json.dump(preset_data, fh, indent=2)

        return skill_success(
            "Export preset saved",
            prompt=(
                "Preset '{}' saved to '{}'. Use load_export_preset to restore these settings.".format(
                    preset_name, preset_path
                )
            ),
            preset_path=preset_path,
            preset_data=preset_data,
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return skill_exception(exc, message="Failed to save export preset")


@skill_entry
def main(**kwargs):
    return save_export_preset(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
