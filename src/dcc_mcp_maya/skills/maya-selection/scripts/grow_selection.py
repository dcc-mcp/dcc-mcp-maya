"""Grow the current component selection by one shell ring."""

# Import local modules
from dcc_mcp_core.skill import skill_error, skill_success


def run(params):  # noqa: ARG001
    """Grow the current component selection.

    Expands the current selection to include all components immediately adjacent
    to the current selection (one ring outward).

    Args:
        params: dict (unused — no parameters required)

    Returns:
        ActionResultModel
    """
    import maya.cmds as cmds

    try:
        before = cmds.ls(selection=True, flatten=True) or []
        cmds.GrowPolygonSelectionRegion()
        after = cmds.ls(selection=True, flatten=True) or []
        added = len(after) - len(before)
        return skill_success(
            "Grew selection: {} -> {} components".format(len(before), len(after)),
            prompt="Use shrink_selection to undo, or convert_selection to switch modes.",
            before_count=len(before),
            after_count=len(after),
            added=added,
            selection=after,
        )
    except Exception as exc:
        return skill_error(
            "Failed to grow selection",
            str(exc),
            prompt="Ensure a mesh component is selected before calling grow_selection.",
        )
