"""Apply a render quality preset to the Maya Software render globals."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import base64
import logging
import os
import tempfile
from typing import Optional

logger = logging.getLogger(__name__)


def set_render_quality(preset: str = "medium") -> dict:
    """Apply a render quality preset to the Maya Software render globals.

    Presets control anti-aliasing, shading samples and ray depth on the
    ``defaultRenderQuality`` node.

    Args:
        preset: One of ``"low"``, ``"medium"``, or ``"high"``.
            Default: ``"medium"``.

    Returns:
        ActionResultModel dict with ``context.preset`` and
        ``context.applied`` (dict of attribute names and values set).
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    preset_key = preset.lower()
    if preset_key not in _RENDER_QUALITY_PRESETS:
        return error_result(
            "Invalid preset: {}".format(preset),
            "Supported presets: {}".format(", ".join(sorted(_RENDER_QUALITY_PRESETS))),
        ).to_dict()

    attrs = _RENDER_QUALITY_PRESETS[preset_key]

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        node = "defaultRenderQuality"
        applied = {}
        for attr_name, value in attrs.items():
            plug = "{}.{}".format(node, attr_name)
            if cmds.objExists(plug):
                cmds.setAttr(plug, value)
                applied[attr_name] = value

        return success_result(
            "Applied '{}' render quality preset".format(preset_key),
            preset=preset_key,
            applied=applied,
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("set_render_quality failed")
        return error_result("Failed to set render quality preset '{}'".format(preset), str(exc)).to_dict()



def main(**kwargs):
    return set_render_quality(**kwargs)


if __name__ == "__main__":
    import json
    result = set_render_quality()
    print(json.dumps(result))
