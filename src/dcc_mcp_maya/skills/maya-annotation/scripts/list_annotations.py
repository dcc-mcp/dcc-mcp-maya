"""List all annotation nodes in the scene."""

# Import future modules
from __future__ import annotations

# Import built-in modules
# Import local modules
from dcc_mcp_core.skill import skill_entry, skill_error, skill_exception, skill_success


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

        return skill_success(
            "Found {} annotation(s)".format(len(annotations)),
            prompt="Use update_annotation to change text, or delete_annotation to remove one.",
            annotations=annotations,
            count=len(annotations),
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return skill_exception(exc, message="Failed to list annotations")


@skill_entry
def main(**kwargs):
    return list_annotations(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
