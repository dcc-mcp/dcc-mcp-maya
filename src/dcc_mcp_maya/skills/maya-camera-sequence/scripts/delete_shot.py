"""Delete a Maya shot node from the camera sequencer."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging

logger = logging.getLogger(__name__)


def delete_shot(shot_node: str) -> dict:
    """Delete a shot node from the camera sequencer.

    Args:
        shot_node: Name of the shot node to delete.

    Returns:
        ActionResultModel dict with ``shot_node`` (the deleted node name).
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not cmds.objExists(shot_node):
            return error_result(
                "Shot not found: {}".format(shot_node),
                "Verify the shot node name with list_shots",
            ).to_dict()

        cmds.shot(shot_node, edit=True, lock=False)
        cmds.delete(shot_node)

        return success_result(
            "Deleted shot '{}'".format(shot_node),
            prompt="Use list_shots to confirm deletion or create_shot to add a new one.",
            shot_node=shot_node,
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("delete_shot failed")
        return error_result("Failed to delete shot", str(exc)).to_dict()


def main(**kwargs):
    return delete_shot(**kwargs)


if __name__ == "__main__":
    import json

    print(json.dumps(delete_shot("shot1")))
