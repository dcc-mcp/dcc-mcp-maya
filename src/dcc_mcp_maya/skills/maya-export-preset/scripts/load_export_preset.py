"""Load a previously saved Maya export preset and apply its settings."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import json
import logging
import os

logger = logging.getLogger(__name__)


def load_export_preset(preset_path: str, apply_frame_range: bool = True) -> dict:
    """Load a JSON export preset and apply frame range settings.

    Args:
        preset_path: Full path to the ``.json`` preset file.
        apply_frame_range: Whether to apply frame range to the Maya timeline.
            Default ``True``.

    Returns:
        ActionResultModel dict with ``context.preset_data`` and
        ``context.applied_frame_range``.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not os.path.isfile(preset_path):
            return error_result(
                "File not found",
                "Preset file '{}' does not exist".format(preset_path),
            ).to_dict()

        with open(preset_path, "r") as fh:
            preset_data = json.load(fh)

        if apply_frame_range and "frame_range" in preset_data:
            start, end = preset_data["frame_range"]
            cmds.playbackOptions(
                minTime=start,
                maxTime=end,
                animationStartTime=start,
                animationEndTime=end,
            )

        return success_result(
            "Export preset loaded",
            prompt=(
                "Preset '{}' loaded. format={}, frame_range={}.".format(
                    preset_data.get("preset_name", ""),
                    preset_data.get("format", ""),
                    preset_data.get("frame_range"),
                )
            ),
            preset_data=preset_data,
            applied_frame_range=apply_frame_range,
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("load_export_preset failed")
        return error_result("Failed to load export preset", str(exc)).to_dict()


def main(**kwargs):
    return load_export_preset(**kwargs)


if __name__ == "__main__":
    import json as _json

    result = load_export_preset("/path/to/preset.json")
    print(_json.dumps(result))
