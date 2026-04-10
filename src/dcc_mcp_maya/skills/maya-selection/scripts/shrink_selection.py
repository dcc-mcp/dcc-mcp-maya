"""Shrink the current component selection by one shell ring."""
from dcc_mcp_core import error_result, success_result


def run(params):  # noqa: ARG001
    """Shrink the current component selection.

    Contracts the current selection by removing all boundary components
    (one ring inward).

    Args:
        params: dict (unused — no parameters required)

    Returns:
        ActionResultModel
    """
    import maya.cmds as cmds

    try:
        before = cmds.ls(selection=True, flatten=True) or []
        cmds.ShrinkPolygonSelectionRegion()
        after = cmds.ls(selection=True, flatten=True) or []
        removed = len(before) - len(after)
        return success_result(
            "Shrank selection: {} -> {} components".format(len(before), len(after)),
            prompt="Use grow_selection to expand again, or convert_selection to change mode.",
            before_count=len(before),
            after_count=len(after),
            removed=removed,
            selection=after,
        )
    except Exception as exc:
        return error_result(
            "Failed to shrink selection",
            str(exc),
            prompt="Ensure a mesh component is selected before calling shrink_selection.",
        )
