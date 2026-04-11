"""Delete a Maya shot node from the camera sequencer."""

# Import future modules
from __future__ import annotations

# Import built-in modules
# Import local modules
from dcc_mcp_core.skill import skill_entry, skill_error, skill_exception, skill_success

from dcc_mcp_maya.api import validate_node_exists


def delete_shot(shot_node: str) -> dict:
    """Delete a shot node from the camera sequencer.

    Args:
        shot_node: Name of the shot node to delete.

    Returns:
        ActionResultModel dict with ``shot_node`` (the deleted node name).
    """
    try:
        import maya.cmds as cmds  # noqa: PLC0415

        err = validate_node_exists(cmds, shot_node)
        if err:
            return err

        cmds.shot(shot_node, edit=True, lock=False)
        cmds.delete(shot_node)

        return skill_success(
            "Deleted shot '{}'".format(shot_node),
            prompt="Use list_shots to confirm deletion or create_shot to add a new one.",
            shot_node=shot_node,
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return skill_exception(exc, message="Failed to delete shot")


@skill_entry
def main(**kwargs):
    return delete_shot(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main
    run_main(main)
