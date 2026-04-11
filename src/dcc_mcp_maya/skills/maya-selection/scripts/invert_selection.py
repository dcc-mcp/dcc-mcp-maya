"""Invert the current selection within its context."""

# Import local modules
from dcc_mcp_maya.api import maya_error, maya_success


def run(params):  # noqa: ARG001
    """Invert the current selection.

    For object mode: deselects currently selected objects and selects all others.
    For component mode: inverts within the current component context.

    Args:
        params: dict (unused — no parameters required)

    Returns:
        ActionResultModel
    """
    import maya.cmds as cmds

    try:
        before = cmds.ls(selection=True, flatten=True) or []
        cmds.InvertSelection()
        after = cmds.ls(selection=True, flatten=True) or []
        return maya_success(
            "Inverted selection: {} -> {} items".format(len(before), len(after)),
            prompt="Use get_selection (maya-scene) to inspect the result.",
            before_count=len(before),
            after_count=len(after),
            selection=after,
        )
    except Exception as exc:
        return maya_error("Failed to invert selection", str(exc))
