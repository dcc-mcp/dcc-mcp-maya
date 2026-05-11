"""Find Maya nodes by name pattern with an optional type filter."""

from __future__ import annotations

from typing import Optional

from dcc_mcp_core.skill import skill_entry, skill_error, skill_exception, skill_success


def find_by_pattern(pattern: str, type: Optional[str] = "transform") -> dict:  # noqa: A002 - MCP schema uses "type"
    """Find nodes matching a Maya wildcard pattern.

    The default type filter is ``transform`` so common object searches return
    one object entry instead of also matching shape and animation-curve nodes.
    Pass ``type=None`` or an empty string to disable type filtering.
    """
    if not pattern or not str(pattern).strip():
        return skill_error("Pattern is required", "Pass a non-empty Maya wildcard pattern.")

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        node_type = str(type).strip() if type is not None else ""
        if node_type:
            names = cmds.ls(pattern, type=node_type, long=False) or []
        else:
            names = cmds.ls(pattern, long=False) or []
        return skill_success(
            "Found {} object(s)".format(len(names)),
            names=names,
            count=len(names),
            pattern=pattern,
            type=node_type or None,
            prompt="Use the returned names directly for follow-up scene operations.",
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:  # noqa: BLE001
        return skill_exception(exc, message="Failed to find objects by pattern")


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`find_by_pattern`."""
    return find_by_pattern(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
