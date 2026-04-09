"""Set the render globals (resolution, frame range, renderer)."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging
from typing import Optional

logger = logging.getLogger(__name__)


def set_render_settings(
    width: int = 1920,
    height: int = 1080,
    start_frame: Optional[float] = None,
    end_frame: Optional[float] = None,
    renderer: Optional[str] = None,
) -> dict:
    """Set the render globals (resolution, frame range, renderer).

    Args:
        width: Render width in pixels.  Default: 1920.
        height: Render height in pixels.  Default: 1080.
        start_frame: Start frame for batch rendering.  If None, left unchanged.
        end_frame: End frame for batch rendering.  If None, left unchanged.
        renderer: Renderer name (e.g. ``"arnold"``, ``"vray"``, ``"mayaSoftware"``).
            If None, left unchanged.

    Returns:
        ActionResultModel dict with applied render settings.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        cmds.setAttr("defaultResolution.width", width)
        cmds.setAttr("defaultResolution.height", height)
        cmds.setAttr("defaultResolution.deviceAspectRatio", float(width) / float(height))

        applied = {"width": width, "height": height}

        if start_frame is not None:
            cmds.setAttr("defaultRenderGlobals.startFrame", start_frame)
            applied["start_frame"] = start_frame
        if end_frame is not None:
            cmds.setAttr("defaultRenderGlobals.endFrame", end_frame)
            applied["end_frame"] = end_frame
        if renderer is not None:
            cmds.setAttr("defaultRenderGlobals.currentRenderer", renderer, type="string")
            applied["renderer"] = renderer

        return success_result("Render settings applied ({}x{})".format(width, height), **applied).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("set_render_settings failed")
        return error_result("Failed to set render settings", str(exc)).to_dict()



def main(**kwargs):
    return set_render_settings(**kwargs)


if __name__ == "__main__":
    import json
    result = set_render_settings()
    print(json.dumps(result))
