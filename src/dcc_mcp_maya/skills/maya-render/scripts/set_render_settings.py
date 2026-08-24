"""Set Maya render settings."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import math
from typing import Optional

# Import local modules
from dcc_mcp_core.skill import skill_entry, skill_error, skill_exception, skill_success

_FORMAT_CODES = {
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


def set_render_settings(
    width: Optional[int] = None,
    height: Optional[int] = None,
    start_frame: Optional[float] = None,
    end_frame: Optional[float] = None,
    renderer: Optional[str] = None,
    image_format: Optional[str] = None,
    output_path: Optional[str] = None,
    aa_samples: Optional[int] = None,
    diffuse_samples: Optional[int] = None,
    specular_samples: Optional[int] = None,
    transmission_samples: Optional[int] = None,
    sss_samples: Optional[int] = None,
    volume_samples: Optional[int] = None,
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
        aa_samples: Arnold camera (AA) samples, from 0 through 20.
        diffuse_samples: Arnold diffuse samples, from 0 through 20.
        specular_samples: Arnold specular samples, from 0 through 20.
        transmission_samples: Arnold transmission samples, from 0 through 20.
        sss_samples: Arnold subsurface samples, from 0 through 20.
        volume_samples: Arnold volume samples, from 0 through 20.

    Returns:
        ToolResult dict with applied settings.
    """

    previous_attrs = {}
    cmds = None
    try:
        import maya.cmds as cmds  # noqa: PLC0415

        def _write_attr(attr, value, **kwargs):
            if attr not in previous_attrs:
                previous_attrs[attr] = (cmds.getAttr(attr), dict(kwargs))
            cmds.setAttr(attr, value, **kwargs)

        def _rollback():
            for attr, (previous, kwargs) in reversed(list(previous_attrs.items())):
                try:
                    cmds.setAttr(attr, previous, **kwargs)
                except Exception:
                    pass

        sample_values = {
            "aa_samples": ("AASamples", aa_samples),
            "diffuse_samples": ("GIDiffuseSamples", diffuse_samples),
            "specular_samples": ("GISpecularSamples", specular_samples),
            "transmission_samples": ("GITransmissionSamples", transmission_samples),
            "sss_samples": ("GISssSamples", sss_samples),
            "volume_samples": ("GIVolumeSamples", volume_samples),
        }
        requested_samples = {name: pair for name, pair in sample_values.items() if pair[1] is not None}

        if width is not None and (isinstance(width, bool) or not isinstance(width, int) or not 1 <= width <= 8192):
            return skill_error("Invalid render width", "width must be an integer from 1 through 8192")
        if height is not None and (isinstance(height, bool) or not isinstance(height, int) or not 1 <= height <= 8192):
            return skill_error("Invalid render height", "height must be an integer from 1 through 8192")
        for frame_name, value in (("start_frame", start_frame), ("end_frame", end_frame)):
            if value is None:
                continue
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                return skill_error("Invalid {}".format(frame_name), "{} must be a finite number".format(frame_name))
            if not math.isfinite(float(value)) or abs(float(value)) > 1000000:
                return skill_error(
                    "Invalid {}".format(frame_name),
                    "{} is outside the supported range".format(frame_name),
                )
        if start_frame is not None and end_frame is not None and float(start_frame) > float(end_frame):
            return skill_error("Invalid frame range", "start_frame must not exceed end_frame")
        if renderer is not None and (not isinstance(renderer, str) or not renderer or len(renderer) > 128):
            return skill_error("Invalid renderer", "renderer must be a non-empty string of at most 128 characters")
        if image_format is not None and (
            not isinstance(image_format, str) or image_format.lower() not in _FORMAT_CODES
        ):
            return skill_error("Unsupported image format", "Choose a declared Maya image format")
        if output_path is not None and (not isinstance(output_path, str) or not output_path or len(output_path) > 4096):
            return skill_error("Invalid output path", "output_path must be a non-empty string")
        for sample_name, (_attr_name, value) in requested_samples.items():
            if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= 20:
                return skill_error(
                    "Invalid Arnold samples",
                    "{} must be an integer from 0 through 20".format(sample_name),
                )
        if requested_samples:
            active_renderer = renderer or cmds.getAttr("defaultRenderGlobals.currentRenderer")
            if active_renderer != "arnold" or not cmds.objExists("defaultArnoldRenderOptions"):
                return skill_error(
                    "Arnold sampling is unavailable",
                    "Select the Arnold renderer and load MtoA before setting sampling controls.",
                )

        applied = {}
        expected_attrs = {}

        if width is not None:
            _write_attr("defaultResolution.width", width)
            applied["width"] = width
            expected_attrs["defaultResolution.width"] = width
        if height is not None:
            _write_attr("defaultResolution.height", height)
            applied["height"] = height
            expected_attrs["defaultResolution.height"] = height
        if start_frame is not None:
            start_frame = float(start_frame)
            _write_attr("defaultRenderGlobals.startFrame", start_frame)
            applied["start_frame"] = start_frame
            expected_attrs["defaultRenderGlobals.startFrame"] = start_frame
        if end_frame is not None:
            end_frame = float(end_frame)
            _write_attr("defaultRenderGlobals.endFrame", end_frame)
            applied["end_frame"] = end_frame
            expected_attrs["defaultRenderGlobals.endFrame"] = end_frame
        if renderer is not None:
            _write_attr("defaultRenderGlobals.currentRenderer", renderer, type="string")
            applied["renderer"] = renderer
            expected_attrs["defaultRenderGlobals.currentRenderer"] = renderer
        if image_format is not None:
            format_name = image_format.lower()
            fmt_code = _FORMAT_CODES[format_name]
            _write_attr("defaultRenderGlobals.imageFormat", fmt_code)
            expected_attrs["defaultRenderGlobals.imageFormat"] = fmt_code
            active_renderer = renderer or cmds.getAttr("defaultRenderGlobals.currentRenderer")
            arnold_driver = {
                "png": "png",
                "exr": "exr",
                "jpg": "jpeg",
                "jpeg": "jpeg",
                "tif": "tiff",
                "tiff": "tiff",
            }.get(format_name)
            if active_renderer == "arnold" and arnold_driver:
                _write_attr("defaultArnoldDriver.aiTranslator", arnold_driver, type="string")
                expected_attrs["defaultArnoldDriver.aiTranslator"] = arnold_driver
            applied["image_format"] = image_format
        if output_path is not None:
            _write_attr("defaultRenderGlobals.imageFilePrefix", output_path, type="string")
            applied["output_path"] = output_path
            expected_attrs["defaultRenderGlobals.imageFilePrefix"] = output_path
        if requested_samples:
            for sample_name, (attr_name, value) in requested_samples.items():
                attr = "defaultArnoldRenderOptions.{}".format(attr_name)
                _write_attr(attr, value)
                applied[sample_name] = value
                expected_attrs[attr] = value

        if not applied:
            return skill_error("No settings provided", "Specify at least one render setting to update")

        mismatches = {}
        for attr, expected in expected_attrs.items():
            actual = cmds.getAttr(attr)
            if actual != expected:
                mismatches[attr] = {"expected": expected, "actual": actual}
        if mismatches:
            _rollback()
            return skill_error(
                "Render settings did not round-trip",
                "Native Maya readback differs from one or more requested settings.",
                mismatches=mismatches,
                **applied,
            )

        return skill_success(
            "Updated render settings: {}".format(", ".join(applied.keys())),
            prompt="Use render_frame or playblast to render with the new settings.",
            verified=True,
            **applied,
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        if cmds is not None and previous_attrs:
            for attr, (previous, kwargs) in reversed(list(previous_attrs.items())):
                try:
                    cmds.setAttr(attr, previous, **kwargs)
                except Exception:
                    pass
        return skill_exception(exc, message="Failed to set render settings")


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`set_render_settings`."""
    return set_render_settings(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
