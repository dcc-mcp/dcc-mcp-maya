"""List all annotation nodes in the scene."""

# Import future modules
from __future__ import annotations

# Import built-in modules

# Import local modules
from dcc_mcp_maya.api import maya_error, maya_from_exception, maya_success



def list_annotations() -> dict:
    """List all annotation nodes in the current Maya scene.

    Returns:
        ActionResultModel dict with ``context.annotations`` (list of dicts
        with ``annotation_node``, ``transform_node``, ``text``) and
        ``context.count``.
    """
    try:
        import maya.cmds as cmds  # noqa: PLC0415

        annotation_shapes = cmds.ls(type="annotationShape") or []
        annotations = []
        for shape in annotation_shapes:
            text = cmds.getAttr("{}.text".format(shape)) or ""
            parents = cmds.listRelatives(shape, parent=True)
            transform = parents[0] if parents else shape
            annotations.append(
                {
                    "annotation_node": shape,
                    "transform_node": transform,
                    "text": text,
                }
            )

        return maya_success(
            "Found {} annotation(s)".format(len(annotations)),
            prompt="Use update_annotation to change text, or delete_annotation to remove one.",
            annotations=annotations,
            count=len(annotations),
        )
    except ImportError:
        return maya_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return maya_from_exception(exc, "Failed to list annotations")


def main(**kwargs):
    return list_annotations(**kwargs)


if __name__ == "__main__":
    import json

    result = list_annotations()
    print(json.dumps(result))
