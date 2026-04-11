"""Invert the current selection within its context."""

# Import future modules
from __future__ import annotations

# Import local modules
from dcc_mcp_core.skill import skill_entry, skill_exception, skill_success


def invert_selection() -> dict:
    """Invert the current selection.

    For object mode: deselects currently selected objects and selects all others.
    For component mode: inverts within the current component context.

    Returns:
        ActionResultModel dict with ``context.before_count``, ``context.after_count``.
    """
    try:
        import maya.cmds as cmds  # noqa: PLC0415

        before = cmds.ls(selection=True, flatten=True) or []
        cmds.InvertSelection()
        after = cmds.ls(selection=True, flatten=True) or []
        return skill_success(
            "Inverted selection: {} -> {} items".format(len(before), len(after)),
            prompt="Use get_selection (maya-scene) to inspect the result.",
            before_count=len(before),
            after_count=len(after),
            selection=after,
        )
    except Exception as exc:
        return skill_exception(exc, message="Failed to invert selection")


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`invert_selection`."""
    return invert_selection(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
