"""Set Maya render settings."""

# Import future modules
from __future__ import annotations

# Import built-in modules
from typing import Optional

# Import local modules
from dcc_mcp_core.skill import skill_entry, skill_error, skill_exception, skill_success

_VALID_RENDERERS = ("mayaSoftware", "mayaHardware2", "arnold", "vray", "redshift", "renderman")
_VALID_IMAGE_FORMATS = ("png", "exr", "jpg", "jpeg", "tiff", "tga", "bmp", "iff", "sgi", "rla")

# Range constraints for numeric parameters
_NUMERIC_RANGES = {
    "width": (1, 32768),
    "height": (1, 32768),
    "start_frame": (-100000, 100000),
    "end_frame": (-100000, 100000),
}


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
        width: Render width in pixels (1–32768).
        height: Render height in pixels (1–32768).
        start_frame: Animation start frame.
        end_frame: Animation end frame.
        renderer: Render engine name (e.g. ``"mayaSoftware"``, ``"mayaHardware2"``,
            ``"arnold"``, ``"vray"``).
        image_format: Image format string (e.g. ``"png"``, ``"exr"``, ``"jpg"``).
        output_path: Output directory path for rendered images.

    Returns:
        ActionResultModel dict with applied settings.
    """

    # Validate numeric parameter ranges
    for param_name, value in [
        ("width", width),
        ("height", height),
        ("start_frame", start_frame),
        ("end_frame", end_frame),
    ]:
        if value is not None:
            min_val, max_val = _NUMERIC_RANGES[param_name]
            if not isinstance(value, (int, float)) or value < min_val or value > max_val:
                return skill_error(
                    "Invalid render parameters",
                    "'{}' must be between {} and {}".format(param_name, min_val, max_val),
                )

    # Validate frame range order
    if start_frame is not None and end_frame is not None:
        if start_frame > end_frame:
            return skill_error(
                "Invalid frame range",
                "start_frame ({}) must not exceed end_frame ({})".format(start_frame, end_frame),
            )

    # Validate renderer name
    if renderer is not None and renderer not in _VALID_RENDERERS:
        return skill_error(
            "Unknown renderer: {}".format(renderer),
            "Supported renderers: {}".format(", ".join(sorted(_VALID_RENDERERS))),
        )

    # Validate image format
    if image_format is not None and image_format.lower() not in _VALID_IMAGE_FORMATS:
        return skill_error(
            "Unknown image format: {}".format(image_format),
            "Supported formats: {}".format(", ".join(sorted(_VALID_IMAGE_FORMATS))),
        )

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
            return skill_error("No settings provided", "Specify at least one render setting to update")

        return skill_success(
            "Updated render settings: {}".format(", ".join(applied.keys())),
            prompt="Use render_frame or playblast to render with the new settings.",
            **applied,
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return skill_exception(exc, message="Failed to set render settings")


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`set_render_settings`."""
    return set_render_settings(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
