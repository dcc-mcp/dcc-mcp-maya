"""Export animation curves for an object to a Maya .anim file."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging
from typing import List, Optional

logger = logging.getLogger(__name__)


def export_animation_curves(
    object_name: str,
    file_path: str,
    attributes: Optional[List[str]] = None,
    start_frame: Optional[float] = None,
    end_frame: Optional[float] = None,
) -> dict:
    """Export animation curves for an object to a Maya .anim file.

    Uses ``cmds.exportEdits`` (Maya 2013+) to write a Maya ASCII or binary
    file containing only the animation curves driving *object_name*.

    Args:
        object_name: Name of the animated object.
        file_path: Output file path.  Extension determines format:
            ``".anim"`` (Maya native), ``".ma"`` (Maya ASCII),
            ``".mb"`` (Maya Binary).
        attributes: Optional list of attribute names to restrict the export.
            If ``None``, all driven attributes are exported.
        start_frame: First frame of the export range.  ``None`` = scene start.
        end_frame: Last frame of the export range.  ``None`` = scene end.

    Returns:
        ActionResultModel dict with ``context.file_path`` and
        ``context.curve_count``.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not cmds.objExists(object_name):
            return error_result(
                "Object not found: {}".format(object_name),
                "'{}' does not exist in the scene".format(object_name),
            ).to_dict()

        # Resolve frame range
        if start_frame is None:
            start_frame = cmds.playbackOptions(query=True, animationStartTime=True)
        if end_frame is None:
            end_frame = cmds.playbackOptions(query=True, animationEndTime=True)

        # Collect animCurve nodes
        anim_curves = cmds.keyframe(object_name, query=True, name=True) or []
        if attributes:
            filtered = []
            for attr in attributes:
                plug = "{}.{}".format(object_name, attr)
                curves = cmds.keyframe(plug, query=True, name=True) or []
                filtered.extend(curves)
            anim_curves = filtered

        if not anim_curves:
            return error_result(
                "No animation curves found on '{}'".format(object_name),
                "Object has no keyframe data to export",
            ).to_dict()

        # Export via cmds.select + cmds.file
        cmds.select(anim_curves, replace=True)
        export_kwargs = {
            "exportSelected": True,
            "force": True,
            "type": "mayaAscii",
        }  # type: Dict
        ext = file_path.rsplit(".", 1)[-1].lower() if "." in file_path else "ma"
        if ext == "mb":
            export_kwargs["type"] = "mayaBinary"

        cmds.file(file_path, **export_kwargs)
        cmds.select(clear=True)

        return success_result(
            "Exported {} animation curve(s) to '{}'".format(len(anim_curves), file_path),
            file_path=file_path,
            object_name=object_name,
            curve_count=len(anim_curves),
            start_frame=start_frame,
            end_frame=end_frame,
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("export_animation_curves failed")
        return error_result("Failed to export animation curves for '{}'".format(object_name), str(exc)).to_dict()


def main(**kwargs):
    return export_animation_curves(**kwargs)


if __name__ == "__main__":
    import json

    result = export_animation_curves()
    print(json.dumps(result))
