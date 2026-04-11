"""Capture the Maya viewport as a PNG image (base64-encoded)."""

# Import future modules
from __future__ import annotations

# Import local modules
from dcc_mcp_maya.api import maya_error, maya_from_exception, maya_success

# Import built-in modules
import base64
import os
import tempfile
from typing import Optional

def capture_viewport(
    width: int = 1920,
    height: int = 1080,
    frame: Optional[float] = None,
) -> dict:
    """Capture the Maya viewport as a PNG image (base64-encoded).

    Uses ``cmds.playblast`` to render the active viewport into a temporary
    PNG file and returns the image bytes as a Base64 string.

    Args:
        width: Image width in pixels.  Default: 1920.
        height: Image height in pixels.  Default: 1080.
        frame: Frame to capture.  Defaults to the current frame.

    Returns:
        ActionResultModel dict with ``context.image`` (base64 PNG string).
    """

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
        return maya_success(
            "Viewport captured ({}x{} @ frame {})".format(width, height, frame),
            image=encoded,
            width=width,
            height=height,
            frame=frame,
        )
    except ImportError:
        return maya_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return maya_from_exception(exc, "Failed to capture viewport")

def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`capture_viewport`."""
    return capture_viewport(**kwargs)

if __name__ == "__main__":
    import json

    result = capture_viewport()
    print(json.dumps(result))
