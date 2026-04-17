"""Shrink the current component selection by one shell ring."""

# Import future modules
from __future__ import annotations

# Import local modules
from dcc_mcp_core.skill import skill_entry, skill_exception, skill_success


def shrink_selection() -> dict:
    """Shrink the current component selection.

    Contracts the current selection by removing all boundary components
    (one ring inward).

    Returns:
        ToolResult dict with ``context.before_count``, ``context.after_count``.
    """
    try:
        import maya.cmds as cmds  # noqa: PLC0415

        before = cmds.ls(selection=True, flatten=True) or []
        cmds.ShrinkPolygonSelectionRegion()
        after = cmds.ls(selection=True, flatten=True) or []
        removed = len(before) - len(after)
        return skill_success(
            "Shrank selection: {} -> {} components".format(len(before), len(after)),
            prompt="Use grow_selection to expand again, or convert_selection to change mode.",
            before_count=len(before),
            after_count=len(after),
            removed=removed,
            selection=after,
        )
    except Exception as exc:
        return skill_exception(
            exc,
            message="Failed to shrink selection",
            prompt="Ensure a mesh component is selected before calling shrink_selection.",
        )


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`shrink_selection`."""
    return shrink_selection(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
