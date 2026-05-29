"""Export the rigged/animated scene to an interchange file (issue #306).

Final stage: hand the result of the workflow off to other DCCs or a pipeline
by exporting either the whole scene or a selected subset.
"""

from __future__ import annotations

import os
from typing import List, Optional

from dcc_mcp_core.skill import skill_entry

from dcc_mcp_maya.api import maya_error, maya_from_exception, maya_success

_FORMATS = {
    "maya_ascii": ("mayaAscii", ".ma"),
    "maya_binary": ("mayaBinary", ".mb"),
    "obj": ("OBJexport", ".obj"),
    "fbx": ("FBX export", ".fbx"),
}


def export_scene_artifact(
    output_path: str,
    fmt: str = "maya_ascii",
    selection_only: bool = False,
    objects: Optional[List[str]] = None,
) -> dict:
    """Export the scene (or a selection) to ``output_path``.

    Args:
        output_path: Target file path.
        fmt: ``maya_ascii``, ``maya_binary``, ``obj``, or ``fbx``.
        selection_only: Export only the current selection / ``objects``.
        objects: Explicit nodes to select before a selection-only export.

    Returns:
        ToolResult dict with ``context.output_path`` and ``context.fmt``.
    """
    if fmt not in _FORMATS:
        return maya_error(
            "Invalid fmt",
            "fmt must be one of {}".format(", ".join(sorted(_FORMATS))),
        )
    if not output_path:
        return maya_error("Missing output_path", "output_path is required")

    try:
        import maya.cmds as cmds  # noqa: PLC0415
    except ImportError:
        return maya_error(
            "Maya not available",
            "maya.cmds could not be imported",
            possible_solutions=["Run inside Maya or mayapy"],
        )

    try:
        out_dir = os.path.dirname(output_path)
        if out_dir and not os.path.isdir(out_dir):
            os.makedirs(out_dir)

        type_string, ext = _FORMATS[fmt]
        if not output_path.lower().endswith(ext):
            output_path += ext

        export_selected = selection_only or bool(objects)
        if objects:
            missing = [obj for obj in objects if not cmds.objExists(obj)]
            if missing:
                return maya_error("Objects not found", "missing: {}".format(", ".join(missing)))
            cmds.select(objects, replace=True)

        if fmt == "fbx":
            try:
                cmds.loadPlugin("fbxmaya", quiet=True)
            except Exception:  # noqa: BLE001
                pass

        if export_selected:
            cmds.file(output_path, force=True, options="v=0;", type=type_string, exportSelected=True)
            exported = len(cmds.ls(selection=True))
        else:
            cmds.file(output_path, force=True, options="v=0;", type=type_string, exportAll=True)
            exported = len(cmds.ls(transforms=True))

        return maya_success(
            "Exported {} to {}".format(fmt, output_path),
            output_path=output_path,
            fmt=fmt,
            exported_count=exported,
            selection_only=export_selected,
        )
    except Exception as exc:  # noqa: BLE001
        return maya_from_exception(exc, message="Failed to export scene artifact")


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`export_scene_artifact`."""
    return export_scene_artifact(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
