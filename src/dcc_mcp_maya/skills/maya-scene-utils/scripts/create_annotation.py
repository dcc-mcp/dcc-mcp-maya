"""Create a Maya annotation node attached to an object."""

# Import future modules
from __future__ import annotations

# Import built-in modules
from typing import List, Optional

# Import local modules
from dcc_mcp_core.skill import skill_entry, skill_error, skill_exception, skill_success


def create_annotation(
    object_name: str,
    text: str,
    position: Optional[List[float]] = None,
) -> dict:
    """Create a Maya annotation node attached to an object.

    Annotations are text labels that float in the viewport and are linked to
    a specific object via an *annotationShape* node.

    Args:
        object_name: The transform node to annotate.
        text: The annotation text to display.
        position: Optional world-space XYZ offset for the annotation text
            ``[x, y, z]``.  Defaults to slightly above the object's pivot.

    Returns:
        ActionResultModel dict with ``context.annotation_transform``,
        ``context.object_name``, ``context.text``.
    """

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not cmds.objExists(object_name):
            return skill_error(
                "Object not found: {}".format(object_name),
                "'{}' does not exist in the scene".format(object_name),
            )

        if not text:
            return skill_error(
                "Empty annotation text",
                "text must be a non-empty string",
            )

        # Determine annotation position
        if position is not None:
            if len(position) != 3:
                return skill_error(
                    "Invalid position: {}".format(position),
                    "position must be a list of exactly 3 floats [x, y, z]",
                )
            ann_pos = [float(v) for v in position]
        else:
            # Default: slightly above the object pivot
            pivot = cmds.xform(object_name, query=True, rotatePivot=True, worldSpace=True)
            ann_pos = [pivot[0], pivot[1] + 1.0, pivot[2]]

        ann_transform = cmds.annotate(object_name, text=text, point=ann_pos)
        # annotate() returns the shape node; get its parent transform
        ann_parent = cmds.listRelatives(ann_transform, parent=True, fullPath=False)
        ann_transform_name = ann_parent[0] if ann_parent else ann_transform

        return skill_success(
            "Created annotation '{}' on '{}'".format(text, object_name),
            annotation_transform=ann_transform_name,
            annotation_shape=ann_transform,
            object_name=object_name,
            text=text,
            position=ann_pos,
            prompt="Check the result with list_scene_utils or use related actions to continue.",
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return skill_exception(exc, message="Failed to create annotation on '{}'".format(object_name))


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`create_annotation`."""
    return create_annotation(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main
    run_main(main)
