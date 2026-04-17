"""Grow the current component selection by one shell ring."""

# Import future modules
from __future__ import annotations

# Import local modules
from dcc_mcp_core.skill import skill_entry, skill_exception, skill_success


def grow_selection() -> dict:
    """Grow the current component selection.

    Expands the current selection to include all components immediately adjacent
    to the current selection (one ring outward).

    Returns:
        ToolResult dict with ``context.before_count``, ``context.after_count``.
    """
    try:
        import maya.cmds as cmds  # noqa: PLC0415

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
        return skill_exception(
            exc,
            message="Failed to grow selection",
            prompt="Ensure a mesh component is selected before calling grow_selection.",
        )


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`grow_selection`."""
    return grow_selection(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
