"""Capture the Maya viewport as a PNG image (base64-encoded)."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import base64
import os
import tempfile
from typing import Optional

# Import local modules
from dcc_mcp_core.skill import skill_entry, skill_error, skill_exception, skill_success

from dcc_mcp_maya.api import make_input_validator, validate_input

# Pre-build validator for viewport capture parameters
_CAPTURE_VALIDATOR = make_input_validator(
    number_fields={
        "width": (1, 8192),
        "height": (1, 8192),
        "frame": (-100000, 100000),
    },
)


def capture_viewport(
    width: int = 1920,
    height: int = 1080,
    frame: Optional[float] = None,
) -> dict:
    """Capture the Maya viewport as a PNG image (base64-encoded).

    Uses ``cmds.playblast`` to render the active viewport into a temporary
    PNG file and returns the image bytes as a Base64 string.

    Args:
        width: Image width in pixels (1–8192).  Default: 1920.
        height: Image height in pixels (1–8192).  Default: 1080.
        frame: Frame to capture.  Defaults to the current frame.

    Returns:
        ActionResultModel dict with ``context.image`` (base64 PNG string).
    """

    # Validate dimensions
    capture_params = {"width": width, "height": height}
    if frame is not None:
        capture_params["frame"] = frame
    valid, err_msg = validate_input(_CAPTURE_VALIDATOR, capture_params)
    if not valid:
        return skill_error("Invalid capture parameters", err_msg)

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if frame is None:
            frame = cmds.currentTime(query=True)

        # playblast writes  <prefix>.<frame_padded>.png
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            tmp_path = tmp.name

        # Remove the .png suffix for playblast prefix
        prefix = tmp_path[:-4]
        cmds.playblast(
            frame=[frame],
            format="image",
            compression="png",
            filename=prefix,
            width=width,
            height=height,
            percent=100,
            viewer=False,
            showOrnaments=False,
        )

        # playblast appends .<frame>.png
        padded = "{}.{}.png".format(prefix, str(int(frame)).zfill(4))
        img_path = padded if os.path.exists(padded) else prefix + ".png"

        with open(img_path, "rb") as fh:
            img_bytes = fh.read()
        os.unlink(img_path)

        encoded = base64.b64encode(img_bytes).decode("ascii")
        return skill_success(
            "Viewport captured ({}x{} @ frame {})".format(width, height, frame),
            image=encoded,
            width=width,
            height=height,
            frame=frame,
            prompt="Use render_frame for final-quality output.",
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return skill_exception(exc, message="Failed to capture viewport")


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`capture_viewport`."""
    return capture_viewport(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
