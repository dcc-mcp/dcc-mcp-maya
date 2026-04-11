"""Set Maya render settings."""

# Import future modules
from __future__ import annotations

# Import built-in modules
from typing import Optional

# Import local modules
from dcc_mcp_maya.api import maya_error, maya_from_exception, maya_success


def set_render_settings(
    width: Optional[int] = None,
    height: Optional[int] = None,
    start_frame: Optional[float] = None,
    end_frame: Optional[float] = None,
    renderer: Optional[str] = None,
    image_format: Optional[str] = None,
    output_path: Optional[str] = None,
) -> dict:
    """Set Maya render settings.

    Args:
        width: Render width in pixels.
        height: Render height in pixels.
        start_frame: Animation start frame.
        end_frame: Animation end frame.
        renderer: Render engine name (e.g. ``"mayaSoftware"``, ``"mayaHardware2"``,
            ``"arnold"``, ``"vray"``).
        image_format: Image format string (e.g. ``"png"``, ``"exr"``, ``"jpg"``).
        output_path: Output directory path for rendered images.

    Returns:
        ActionResultModel dict with applied settings.
    """

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        applied = {}

        if width is not None:
            cmds.setAttr("defaultResolution.width", width)
            applied["width"] = width
        if height is not None:
            cmds.setAttr("defaultResolution.height", height)
            applied["height"] = height
        if start_frame is not None:
            cmds.setAttr("defaultRenderGlobals.startFrame", start_frame)
            applied["start_frame"] = start_frame
        if end_frame is not None:
            cmds.setAttr("defaultRenderGlobals.endFrame", end_frame)
            applied["end_frame"] = end_frame
        if renderer is not None:
            cmds.setAttr("defaultRenderGlobals.currentRenderer", renderer, type="string")
            applied["renderer"] = renderer
        if image_format is not None:
            # Format code mapping for mayaSoftware
            _fmt_map = {
                "gif": 0,
                "soft": 1,
                "rla": 2,
                "tiff": 3,
                "sgi": 5,
                "jpg": 8,
                "jpeg": 8,
                "eps": 9,
                "iff": 10,
                "png": 32,
                "maya16iff": 13,
                "exr": 40,
                "tga": 19,
                "bmp": 20,
            }
            fmt_code = _fmt_map.get(image_format.lower(), 32)
            cmds.setAttr("defaultRenderGlobals.imageFormat", fmt_code)
            applied["image_format"] = image_format
        if output_path is not None:
            cmds.setAttr("defaultRenderGlobals.imageFilePrefix", output_path, type="string")
            applied["output_path"] = output_path

        if not applied:
            return maya_error("No settings provided", "Specify at least one render setting to update")

        return maya_success(
            "Updated render settings: {}".format(", ".join(applied.keys())),
            prompt="Use render_frame or playblast to render with the new settings.",
            **applied,
        )
    except ImportError:
        return maya_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return maya_from_exception(exc, "Failed to set render settings")


def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`set_render_settings`."""
    return set_render_settings(**kwargs)


if __name__ == "__main__":
    import json

    result = set_render_settings(width=1920, height=1080, renderer="mayaHardware2")
    print(json.dumps(result))
