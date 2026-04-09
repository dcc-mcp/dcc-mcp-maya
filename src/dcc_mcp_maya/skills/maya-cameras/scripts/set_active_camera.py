"""Set the active camera for the current viewport panel."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging
from typing import Optional

logger = logging.getLogger(__name__)


def set_active_camera(camera_name: str, panel: Optional[str] = None) -> dict:
    """Set the active camera for a Maya viewport panel.

    Args:
        camera_name: Name of the camera transform node to activate.
        panel: Optional model panel name (e.g. ``"modelPanel1"``).  If None,
            the first visible model panel is used.

    Returns:
        ActionResultModel dict with ``context.panel`` and ``context.camera_name``.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not cmds.objExists(camera_name):
            return error_result(
                "Camera not found: {}".format(camera_name),
                "'{}' does not exist".format(camera_name),
            ).to_dict()

        if panel is None:
            panels = cmds.getPanel(type="modelPanel") or []
            if not panels:
                return error_result(
                    "No model panel found",
                    "Could not find a visible model panel",
                ).to_dict()
            panel = panels[0]

        cmds.modelPanel(panel, edit=True, camera=camera_name)

        return success_result(
            "Set active camera to '{}' on panel '{}'".format(camera_name, panel),
            prompt="Use get_camera_info to check the camera's current attributes.",
            panel=panel,
            camera_name=camera_name,
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("set_active_camera failed")
        return error_result("Failed to set active camera", str(exc)).to_dict()


def main(**kwargs):
    return set_active_camera(**kwargs)


if __name__ == "__main__":
    import json

    result = set_active_camera("persp")
    print(json.dumps(result))
