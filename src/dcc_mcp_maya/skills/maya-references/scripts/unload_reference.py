"""Unload a file reference without removing it from the scene."""

# Import future modules
from __future__ import annotations

# Import local modules
from dcc_mcp_core.skill import skill_entry, skill_error, skill_exception, skill_success

from dcc_mcp_maya.api import validate_node_exists

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

        err = validate_node_exists(cmds, reference_node)
        if err:
            return err

        if cmds.objectType(reference_node) != "reference":
            return skill_error(
                "Not a reference node: {}".format(reference_node),
                "'{}' is of type '{}'".format(reference_node, cmds.objectType(reference_node)),
            )

        cmds.file(unloadReference=reference_node)

        return skill_success(
            "Unloaded reference '{}'".format(reference_node),
            reference_node=reference_node,
            loaded=False,
            prompt="Check the result with list_references or use related actions to continue.",
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return skill_exception(exc, message="Failed to unload reference '{}'".format(reference_node))


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`unload_reference`."""
    return unload_reference(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main
    run_main(main)
