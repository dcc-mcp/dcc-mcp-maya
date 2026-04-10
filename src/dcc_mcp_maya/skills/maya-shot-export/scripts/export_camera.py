"""Export a shot camera to FBX or Maya ASCII."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging
import os

logger = logging.getLogger(__name__)


def export_camera(
    camera: str,
    file_path: str,
    start_frame: float = 1.0,
    end_frame: float = 100.0,
    file_format: str = "fbx",
) -> dict:
    """Export a shot camera to FBX or Maya ASCII.

    Args:
        camera: Name of the camera transform or shape node to export.
        file_path: Output file path (``.fbx`` or ``.ma``).
        start_frame: Start frame for baked animation.  Default: 1.
        end_frame: End frame for baked animation.  Default: 100.
        file_format: ``"fbx"`` or ``"ma"`` (Maya ASCII).  Default: ``"fbx"``.

    Returns:
        ActionResultModel dict with ``context.file_path``.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not cmds.objExists(camera):
            return error_result(
                "Camera '{}' not found".format(camera),
                "Use list_cameras to find available cameras",
            ).to_dict()

        # Resolve transform node
        cam_type = cmds.objectType(camera)
        if cam_type == "camera":
            parents = cmds.listRelatives(camera, parent=True, fullPath=True) or []
            cam_transform = parents[0] if parents else camera
        else:
            cam_transform = camera

        out_dir = os.path.dirname(os.path.abspath(file_path))
        os.makedirs(out_dir, exist_ok=True)

        if file_format.lower() == "ma":
            cmds.select(cam_transform, replace=True)
            cmds.file(
                file_path,
                exportSelected=True,
                type="mayaAscii",
                force=True,
            )
        else:
            import maya.mel as mel  # noqa: PLC0415
            if not cmds.pluginInfo("fbxmaya", q=True, loaded=True):
                cmds.loadPlugin("fbxmaya")
            cmds.select(cam_transform, replace=True)
            mel.eval("FBXExportBakeComplexAnimation -v 1;")
            mel.eval("FBXExportBakeComplexStart -v {};".format(int(start_frame)))
            mel.eval("FBXExportBakeComplexEnd -v {};".format(int(end_frame)))
            mel.eval('FBXExport -f "{}" -s;'.format(file_path.replace("\\", "/")))

        return success_result(
            "Exported camera '{}' to '{}'".format(cam_transform, file_path),
            prompt="Import this camera file in your compositing or lighting application.",
            file_path=file_path,
            camera=cam_transform,
            file_format=file_format,
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("export_camera failed")
        return error_result("Failed to export camera '{}'".format(camera), str(exc)).to_dict()


def main(**kwargs):
    return export_camera(**kwargs)


if __name__ == "__main__":
    import json

    print(json.dumps(export_camera("persp", "/tmp/cam.fbx")))
