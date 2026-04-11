"""Unload a file reference without removing it from the scene."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging

logger = logging.getLogger(__name__)


def unload_reference(reference_node: str) -> dict:
    """Unload a file reference without removing it from the scene.

    Unloading keeps the reference node intact but removes the referenced
    nodes from memory.  Use :func:`reload_reference` to restore them.

    Args:
        reference_node: Name of the reference node to unload.

    Returns:
        ActionResultModel dict with ``context.reference_node`` and
        ``context.loaded`` (``False`` after success).
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not cmds.objExists(reference_node):
            return error_result(
                "Reference node not found: {}".format(reference_node),
                "'{}' does not exist".format(reference_node),
            ).to_dict()

        if cmds.objectType(reference_node) != "reference":
            return error_result(
                "Not a reference node: {}".format(reference_node),
                "'{}' is of type '{}'".format(reference_node, cmds.objectType(reference_node)),
            ).to_dict()

        cmds.file(unloadReference=reference_node)

        return success_result(
            "Unloaded reference '{}'".format(reference_node),
            reference_node=reference_node,
            loaded=False,
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("unload_reference failed")
        return error_result("Failed to unload reference '{}'".format(reference_node), str(exc)).to_dict()


def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`unload_reference`."""
    return unload_reference(**kwargs)


if __name__ == "__main__":
    import json

    result = unload_reference()
    print(json.dumps(result))
