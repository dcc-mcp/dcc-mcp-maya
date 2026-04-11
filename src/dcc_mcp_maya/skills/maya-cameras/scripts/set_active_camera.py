"""Set the active camera for the current viewport panel."""

# Import future modules
from __future__ import annotations

# Import built-in modules
from typing import Optional

# Import local modules
from dcc_mcp_maya.api import maya_error, maya_from_exception, maya_success


def set_active_camera(camera_name: str, panel: Optional[str] = None) -> dict:
    """Set the active camera for a Maya viewport panel.

    Args:
        camera_name: Name of the camera transform node to activate.
        panel: Optional model panel name (e.g. ``"modelPanel1"``).  If None,
            the first visible model panel is used.

    Returns:
        ActionResultModel dict with ``context.panel`` and ``context.camera_name``.
    """
    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not cmds.objExists(camera_name):
            return maya_error(
                "Camera not found: {}".format(camera_name),
                "'{}' does not exist".format(camera_name),
            )

        if panel is None:
            panels = cmds.getPanel(type="modelPanel") or []
            if not panels:
                return maya_error(
                    "No model panel found",
                    "Could not find a visible model panel",
                )
            panel = panels[0]

        cmds.modelPanel(panel, edit=True, camera=camera_name)

        return maya_success(
            "Set active camera to '{}' on panel '{}'".format(camera_name, panel),
            prompt="Use get_camera_info to check the camera's current attributes.",
            panel=panel,
            camera_name=camera_name,
        )
    except ImportError:
        return maya_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return maya_from_exception(exc, "Failed to set active camera")


def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`set_active_camera`."""
    return set_active_camera(**kwargs)


if __name__ == "__main__":
    import json

    result = set_active_camera("persp")
    print(json.dumps(result))
