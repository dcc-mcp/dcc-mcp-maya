"""Return the current Maya selection."""

# Import future modules
from __future__ import annotations

# Import local modules
from dcc_mcp_core.skill import skill_entry, skill_error, skill_exception, skill_success


def get_selection() -> dict:
    """Return the current Maya selection.

    Returns:
        ActionResultModel dict with ``context.selection`` list.
    """

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        selection = cmds.ls(selection=True) or []
        return skill_success(
            f"{len(selection)} objects selected",
            selection=selection,
            count=len(selection),
            prompt="Check the result with list_scene or use related actions to continue.",
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return skill_exception(exc, message="Failed to get selection")


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`get_selection`."""
    return get_selection(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main
    run_main(main)
