"""List all annotation nodes in the scene."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging

logger = logging.getLogger(__name__)


def list_annotations() -> dict:
    """List all annotation nodes in the current Maya scene.

    Returns:
        ActionResultModel dict with ``context.annotations`` (list of dicts
        with ``annotation_node``, ``transform_node``, ``text``) and
        ``context.count``.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

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

        return success_result(
            "Found {} annotation(s)".format(len(annotations)),
            prompt="Use update_annotation to change text, or delete_annotation to remove one.",
            annotations=annotations,
            count=len(annotations),
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("list_annotations failed")
        return error_result("Failed to list annotations", str(exc)).to_dict()


def main(**kwargs):
    return list_annotations(**kwargs)


if __name__ == "__main__":
    import json

    result = list_annotations()
    print(json.dumps(result))
