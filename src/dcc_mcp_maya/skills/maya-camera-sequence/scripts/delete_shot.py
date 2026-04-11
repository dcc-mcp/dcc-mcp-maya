"""Delete a Maya shot node from the camera sequencer."""

# Import future modules
from __future__ import annotations

# Import built-in modules

# Import local modules
from dcc_mcp_maya.api import maya_error, maya_from_exception, maya_success


def delete_shot(shot_node: str) -> dict:
    """Delete a shot node from the camera sequencer.

    Args:
        shot_node: Name of the shot node to delete.

    Returns:
        ActionResultModel dict with ``shot_node`` (the deleted node name).
    """
    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not cmds.objExists(shot_node):
            return maya_error(
                "Shot not found: {}".format(shot_node),
                "Verify the shot node name with list_shots",
            )

        cmds.shot(shot_node, edit=True, lock=False)
        cmds.delete(shot_node)

        return maya_success(
            "Deleted shot '{}'".format(shot_node),
            prompt="Use list_shots to confirm deletion or create_shot to add a new one.",
            shot_node=shot_node,
        )
    except ImportError:
        return maya_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return maya_from_exception(exc, "Failed to delete shot")


def main(**kwargs):
    return delete_shot(**kwargs)


if __name__ == "__main__":
    import json

    print(json.dumps(delete_shot("shot1")))
