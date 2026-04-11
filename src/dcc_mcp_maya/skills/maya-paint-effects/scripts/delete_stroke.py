"""Delete one or all Paint Effects stroke nodes."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging
from typing import Optional

logger = logging.getLogger(__name__)


# Import local modules
from dcc_mcp_core.skill import skill_entry, skill_error, skill_exception, skill_success  # noqa: E402


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

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if delete_all:
            stroke_nodes = cmds.ls(type="stroke") or []
        elif stroke:
            if not cmds.objExists(stroke):
                return skill_error(
                    "Stroke not found: {}".format(stroke),
                    "Verify the stroke node name with list_strokes",
                )
            stroke_nodes = [stroke]
        else:
            return skill_error(
                "No stroke specified",
                "Provide 'stroke' node name or set 'delete_all=True'",
            )

        deleted = []
        for sn in stroke_nodes:
            parents = cmds.listRelatives(sn, parent=True) or []
            target = parents[0] if parents else sn
            try:
                cmds.delete(target)
                deleted.append(target)
            except Exception as exc:
                logger.warning("Could not delete %s: %s", target, exc)

        return skill_success(
            "Deleted {} Paint Effects stroke(s)".format(len(deleted)),
            prompt="Use list_strokes to confirm deletion or create_stroke to add new ones.",
            deleted=deleted,
            count=len(deleted),
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return skill_exception(exc, message="Failed to delete Paint Effects stroke")


@skill_entry
def main(**kwargs):
    return delete_stroke(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main
    run_main(main)
