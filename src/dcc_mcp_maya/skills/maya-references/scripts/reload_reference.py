"""Reload a previously unloaded (or modified) file reference."""

# Import future modules
from __future__ import annotations

# Import local modules
from dcc_mcp_core.skill import skill_entry, skill_error, skill_exception, skill_success

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
            return skill_error(
                "Reference node not found: {}".format(reference_node),
                "'{}' does not exist".format(reference_node),
            )

        if cmds.objectType(reference_node) != "reference":
            return skill_error(
                "Not a reference node: {}".format(reference_node),
                "'{}' is of type '{}'".format(reference_node, cmds.objectType(reference_node)),
            )

        cmds.file(loadReference=reference_node)

        try:
            file_path = cmds.referenceQuery(reference_node, filename=True, withoutCopyNumber=True)
        except Exception:
            file_path = ""

        return skill_success(
            "Reloaded reference '{}'".format(reference_node),
            reference_node=reference_node,
            file_path=file_path,
            loaded=True,
            prompt="Use list_references to confirm the reference status.",
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return skill_exception(exc, message="Failed to reload reference '{}'".format(reference_node))


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`reload_reference`."""
    return reload_reference(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main
    run_main(main)
