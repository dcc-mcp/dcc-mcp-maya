"""Export selected geometry within a frame range to FBX."""

# Import future modules
from __future__ import annotations

# Import local modules
from dcc_mcp_maya.api import maya_error, maya_from_exception, maya_success

# Import built-in modules
import os
from typing import List, Optional


def export_shot_fbx(
    file_path: str,
    objects: Optional[List[str]] = None,
    start_frame: Optional[float] = None,
    end_frame: Optional[float] = None,
    bake_animation: bool = True,
) -> dict:
    """Export selected geometry within a frame range to FBX.

    Args:
        file_path: Output ``.fbx`` file path (created if missing).
        objects: Objects to export.  If None, current selection is used.
        start_frame: Start frame.  Defaults to timeline start.
        end_frame: End frame.  Defaults to timeline end.
        bake_animation: Bake animation curves before export.  Default: True.

    Returns:
        ActionResultModel dict with ``context.file_path`` and frame range.
    """

    try:
        import maya.cmds as cmds  # noqa: PLC0415
        import maya.mel as mel  # noqa: PLC0415

        if objects:
            cmds.select(objects, replace=True)
        elif not cmds.ls(selection=True):
            return maya_error(
                "Nothing selected",
                "Provide 'objects' or select nodes in Maya",
            )

        sf = start_frame if start_frame is not None else cmds.playbackOptions(q=True, minTime=True)
        ef = end_frame if end_frame is not None else cmds.playbackOptions(q=True, maxTime=True)

        out_dir = os.path.dirname(os.path.abspath(file_path))
        os.makedirs(out_dir, exist_ok=True)

        # Load FBX plugin if needed
        if not cmds.pluginInfo("fbxmaya", q=True, loaded=True):
            cmds.loadPlugin("fbxmaya")

        mel.eval("FBXExportBakeComplexAnimation -v {};".format(1 if bake_animation else 0))
        mel.eval("FBXExportBakeComplexStart -v {};".format(int(sf)))
        mel.eval("FBXExportBakeComplexEnd -v {};".format(int(ef)))
        mel.eval('FBXExport -f "{}" -s;'.format(file_path.replace("\\", "/")))

        return maya_success(
            "Exported FBX to '{}'".format(file_path),
            prompt="Use import_file or export_shot_alembic for alternative formats.",
            file_path=file_path,
            start_frame=sf,
            end_frame=ef,
        )
    except ImportError:
        return maya_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return maya_from_exception(exc, "Failed to export FBX")


def main(**kwargs):
    return export_shot_fbx(**kwargs)


if __name__ == "__main__":
    import json

    print(json.dumps(export_shot_fbx("/tmp/shot_001.fbx")))
