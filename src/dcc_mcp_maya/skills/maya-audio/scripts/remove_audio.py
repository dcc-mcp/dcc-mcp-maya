"""Delete a sound node from the scene."""

# Import future modules
from __future__ import annotations

# Import built-in modules
# Import local modules
from dcc_mcp_maya.api import maya_error, maya_from_exception, maya_success


def remove_audio(sound_node: str) -> dict:
    """Delete a sound node from the Maya scene.

    Args:
        sound_node: Name of the audio/sound node to delete.

    Returns:
        ActionResultModel dict with ``context.deleted_node``.
    """
    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not cmds.objExists(sound_node):
            return maya_error(
                "Sound node not found: {}".format(sound_node),
                "'{}' does not exist in the scene".format(sound_node),
            )

        node_type = cmds.objectType(sound_node)
        if node_type != "audio":
            return maya_error(
                "Not a sound node: {}".format(sound_node),
                "Expected an 'audio' node, got '{}'".format(node_type),
            )

        cmds.delete(sound_node)

        return maya_success(
            "Deleted sound node '{}'".format(sound_node),
            prompt="Use list_audio to confirm deletion.",
            deleted_node=sound_node,
        )
    except ImportError:
        return maya_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return maya_from_exception(exc, "Failed to remove audio")


def main(**kwargs):
    return remove_audio(**kwargs)


if __name__ == "__main__":
    import json

    result = remove_audio("sound1")
    print(json.dumps(result))
