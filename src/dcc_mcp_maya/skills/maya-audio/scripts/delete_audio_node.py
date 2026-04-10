"""Delete a sound node from the Maya scene."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging

logger = logging.getLogger(__name__)


def delete_audio_node(sound_node: str) -> dict:
    """Delete a sound/audio node from the scene.

    Args:
        sound_node: Name of the sound/audio node to delete.

    Returns:
        ActionResultModel dict with ``context.sound_node``.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    if not sound_node:
        return error_result("Invalid sound_node", "sound_node must not be empty").to_dict()

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not cmds.objExists(sound_node):
            return error_result(
                "Sound node not found: '{}'".format(sound_node),
                "Use list_audio_nodes to see available sound nodes.",
            ).to_dict()

        node_type = cmds.objectType(sound_node)
        if node_type not in ("audio", "sound"):
            return error_result(
                "Node '{}' is not an audio node (type: {})".format(sound_node, node_type),
                "Only audio/sound node types can be deleted with this action.",
            ).to_dict()

        cmds.delete(sound_node)

        return success_result(
            "Deleted audio node '{}'".format(sound_node),
            prompt="Audio node removed. Use import_audio to add a new one.",
            sound_node=sound_node,
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("delete_audio_node failed")
        return error_result("Failed to delete audio node", str(exc)).to_dict()


def main(**kwargs) -> dict:
    return delete_audio_node(**kwargs)


if __name__ == "__main__":
    import json

    print(json.dumps(delete_audio_node("sound1")))
