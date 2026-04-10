"""Delete one or all Paint Effects stroke nodes."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging
from typing import Optional

logger = logging.getLogger(__name__)


def delete_stroke(
    stroke: Optional[str] = None,
    delete_all: bool = False,
) -> dict:
    """Delete a Paint Effects stroke node and its transform parent.

    Args:
        stroke: Name of the stroke *shape* node to delete.  Ignored when
            ``delete_all`` is ``True``.
        delete_all: If ``True``, delete every stroke in the scene.

    Returns:
        ActionResultModel dict with ``deleted`` list of removed nodes.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if delete_all:
            stroke_nodes = cmds.ls(type="stroke") or []
        elif stroke:
            if not cmds.objExists(stroke):
                return error_result(
                    "Stroke not found: {}".format(stroke),
                    "Verify the stroke node name with list_strokes",
                ).to_dict()
            stroke_nodes = [stroke]
        else:
            return error_result(
                "No stroke specified",
                "Provide 'stroke' node name or set 'delete_all=True'",
            ).to_dict()

        deleted = []
        for sn in stroke_nodes:
            parents = cmds.listRelatives(sn, parent=True) or []
            target = parents[0] if parents else sn
            try:
                cmds.delete(target)
                deleted.append(target)
            except Exception as exc:
                logger.warning("Could not delete %s: %s", target, exc)

        return success_result(
            "Deleted {} Paint Effects stroke(s)".format(len(deleted)),
            prompt="Use list_strokes to confirm deletion or create_stroke to add new ones.",
            deleted=deleted,
            count=len(deleted),
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("delete_stroke failed")
        return error_result("Failed to delete Paint Effects stroke", str(exc)).to_dict()


def main(**kwargs):
    return delete_stroke(**kwargs)


if __name__ == "__main__":
    import json

    print(json.dumps(delete_stroke(delete_all=True)))
