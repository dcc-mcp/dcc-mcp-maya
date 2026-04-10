"""Delete a sound node from the scene."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging

logger = logging.getLogger(__name__)


def remove_audio(sound_node: str) -> dict:
    """Delete a sound node from the Maya scene.

    Args:
        sound_node: Name of the audio/sound node to delete.

    Returns:
        ActionResultModel dict with ``context.deleted_node``.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not cmds.objExists(sound_node):
            return error_result(
                "Sound node not found: {}".format(sound_node),
                "'{}' does not exist in the scene".format(sound_node),
            ).to_dict()

        node_type = cmds.objectType(sound_node)
        if node_type != "audio":
            return error_result(
                "Not a sound node: {}".format(sound_node),
                "Expected an 'audio' node, got '{}'".format(node_type),
            ).to_dict()

        cmds.delete(sound_node)

        return success_result(
            "Deleted sound node '{}'".format(sound_node),
            prompt="Use list_audio to confirm deletion.",
            deleted_node=sound_node,
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("remove_audio failed")
        return error_result("Failed to remove audio", str(exc)).to_dict()


def main(**kwargs):
    return remove_audio(**kwargs)


if __name__ == "__main__":
    import json

    result = remove_audio("sound1")
    print(json.dumps(result))
