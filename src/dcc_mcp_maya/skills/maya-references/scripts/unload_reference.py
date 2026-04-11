"""Unload a file reference without removing it from the scene."""

# Import future modules
from __future__ import annotations

# Import local modules
from dcc_mcp_maya.api import maya_error, maya_from_exception, maya_success

# Import built-in modules


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

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not cmds.objExists(reference_node):
            return maya_error(
                "Reference node not found: {}".format(reference_node),
                "'{}' does not exist".format(reference_node),
            )

        if cmds.objectType(reference_node) != "reference":
            return maya_error(
                "Not a reference node: {}".format(reference_node),
                "'{}' is of type '{}'".format(reference_node, cmds.objectType(reference_node)),
            )

        cmds.file(unloadReference=reference_node)

        return maya_success(
            "Unloaded reference '{}'".format(reference_node),
            reference_node=reference_node,
            loaded=False,
            prompt="Check the result with list_references or use related actions to continue.",
        )
    except ImportError:
        return maya_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return maya_from_exception(exc, "Failed to unload reference '{}'".format(reference_node))


def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`unload_reference`."""
    return unload_reference(**kwargs)


if __name__ == "__main__":
    import json

    result = unload_reference()
    print(json.dumps(result))
