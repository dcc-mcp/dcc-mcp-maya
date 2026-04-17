"""Create a text annotation attached to an object or world position."""

# Import future modules
from __future__ import annotations

# Import built-in modules
from typing import List, Optional

# Import local modules
from dcc_mcp_core.skill import skill_entry, skill_error, skill_exception, skill_success


def create_annotation(
    text: str,
    target_object: Optional[str] = None,
    position: Optional[List[float]] = None,
    name: Optional[str] = None,
) -> dict:
    """Create a viewport text annotation.

    Creates a Maya annotation node that displays text in the viewport.
    The annotation can be attached to an existing object or placed at a
    specific world-space position.

    Works in both interactive Maya and mayapy standalone (batch mode).

    Args:
        text: The annotation text to display.
        target_object: If provided, the annotation will be parented to this
            object and follow it as it moves.
        position: ``[x, y, z]`` world-space position offset for the annotation.
            Defaults to ``[0, 1, 0]`` (one unit above origin).
        name: Optional name for the annotation transform node.

    Returns:
        ToolResult dict with ``context.annotation_node`` and
        ``context.transform_node``.
    """
    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if target_object and not cmds.objExists(target_object):
            return skill_error(
                "Object not found: {}".format(target_object),
                "'{}' does not exist in the scene".format(target_object),
            )

        pos = position if position and len(position) == 3 else [0.0, 1.0, 0.0]
        annotation_node = None
        transform_node = None

        if target_object:
            # Annotate attached to an existing object
            result = cmds.annotate(target_object, text=text, point=pos)
            annotation_node = result if isinstance(result, str) else result[0]
            transform_node = cmds.listRelatives(annotation_node, parent=True)[0]
        else:
            # World-space: cmds.annotate requires a target transform.
            # Use a temporary locator so annotate() works in interactive Maya.
            # In mayapy standalone, annotate may fail — fall back to createNode.
            loc = None
            try:
                loc = cmds.spaceLocator(name="_ann_loc_tmp")[0]
                cmds.move(pos[0], pos[1], pos[2], loc, absolute=True)
                result = cmds.annotate(loc, text=text, point=pos)
                annotation_node = result if isinstance(result, str) else result[0]
                ann_xform = cmds.listRelatives(annotation_node, parent=True)[0]
                # Re-parent to world before deleting the locator
                cmds.parent(ann_xform, world=True)
                transform_node = ann_xform
            except Exception:
                # Fallback for mayapy standalone / batch mode where annotate is unavailable
                transform_node = cmds.createNode("transform", name=name or "annotation1")
                annotation_node = cmds.createNode("annotationShape", parent=transform_node)
                cmds.setAttr("{}.text".format(annotation_node), text, type="string")
                cmds.move(pos[0], pos[1], pos[2], transform_node, absolute=True)
                # name was used for createNode — skip rename below
                name = None
            finally:
                if loc and cmds.objExists(loc):
                    cmds.delete(loc)

        if name and transform_node and cmds.objExists(transform_node):
            try:
                transform_node = cmds.rename(transform_node, name)
            except Exception:
                pass

        return skill_success(
            "Created annotation '{}'".format(text[:40]),
            prompt="Use update_annotation to change the text, or list_annotations to see all annotations.",
            annotation_node=annotation_node,
            transform_node=transform_node,
            text=text,
            position=pos,
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return skill_exception(exc, message="Failed to create annotation")


@skill_entry
def main(**kwargs):
    return create_annotation(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
