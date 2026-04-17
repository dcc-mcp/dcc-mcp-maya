"""Delete a sound node from the scene."""

# Import future modules
from __future__ import annotations

# Import built-in modules
# Import local modules
from dcc_mcp_core.skill import skill_entry, skill_error, skill_exception, skill_success

from dcc_mcp_maya.api import validate_node_exists


def remove_audio(sound_node: str) -> dict:
    """Delete a sound node from the Maya scene.

    Args:
        sound_node: Name of the audio/sound node to delete.

    Returns:
        ToolResult dict with ``context.deleted_node``.
    """
    try:
        import maya.cmds as cmds  # noqa: PLC0415

        err = validate_node_exists(cmds, sound_node)
        if err:
            return err

        node_type = cmds.objectType(sound_node)
        if node_type != "audio":
            return skill_error(
                "Not a sound node: {}".format(sound_node),
                "Expected an 'audio' node, got '{}'".format(node_type),
            )

        cmds.delete(sound_node)

        return skill_success(
            "Deleted sound node '{}'".format(sound_node),
            prompt="Use list_audio to confirm deletion.",
            deleted_node=sound_node,
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return skill_exception(exc, message="Failed to remove audio")


@skill_entry
def main(**kwargs):
    return remove_audio(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
