"""Export animation curves for an object to a Maya .anim file."""

# Import future modules
from __future__ import annotations

# Import built-in modules
from typing import List, Optional

# Import local modules
from dcc_mcp_core.skill import skill_entry, skill_error, skill_exception, skill_success


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
    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not cmds.objExists(object_name):
            return skill_error(
                "Object not found: {}".format(object_name),
                "'{}' does not exist in the scene".format(object_name),
            )

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
            return skill_error(
                "No animation curves found on '{}'".format(object_name),
                "Object has no keyframe data to export",
            )

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

        return skill_success(
            "Exported {} animation curve(s) to '{}'".format(len(anim_curves), file_path),
            file_path=file_path,
            object_name=object_name,
            curve_count=len(anim_curves),
            start_frame=start_frame,
            end_frame=end_frame,
            prompt="Use import_animation_curves to restore the curves on another rig.",
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return skill_exception(exc, message="Failed to export animation curves for '{}'".format(object_name))


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`export_animation_curves`."""
    return export_animation_curves(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main
    run_main(main)
