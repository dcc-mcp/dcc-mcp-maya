"""Reload a previously unloaded (or modified) file reference."""

# Import future modules
from __future__ import annotations

# Import local modules
from dcc_mcp_maya.api import maya_error, maya_from_exception, maya_success

# Import built-in modules

def reload_reference(reference_node: str) -> dict:
    """Reload a previously unloaded (or modified) file reference.

    Args:
        reference_node: Name of the reference node to reload
            (e.g. ``"characterRN"``).  Use :func:`list_references` to
            discover reference nodes.

    Returns:
        ActionResultModel dict with ``context.reference_node``,
        ``context.file_path``, and ``context.loaded``.
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

        cmds.file(loadReference=reference_node)

        try:
            file_path = cmds.referenceQuery(reference_node, filename=True, withoutCopyNumber=True)
        except Exception:
            file_path = ""

        return maya_success(
            "Reloaded reference '{}'".format(reference_node),
            reference_node=reference_node,
            file_path=file_path,
            loaded=True,
        )
    except ImportError:
        return maya_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return maya_from_exception(exc, "Failed to reload reference '{}'".format(reference_node))

def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`reload_reference`."""
    return reload_reference(**kwargs)

if __name__ == "__main__":
    import json

    result = reload_reference()
    print(json.dumps(result))
