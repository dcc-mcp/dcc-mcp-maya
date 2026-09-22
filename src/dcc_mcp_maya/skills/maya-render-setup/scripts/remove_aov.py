"""Disconnect and delete an Arnold AOV."""

from __future__ import annotations

from typing import Optional

from dcc_mcp_core.skill import skill_entry

from dcc_mcp_maya.api import maya_error, maya_from_exception, maya_success
from dcc_mcp_maya.render_setup import RenderSetupContractError
from dcc_mcp_maya.render_setup import remove_aov as _remove_aov


def remove_aov(aov: Optional[str] = None) -> dict:
    """Remove an AOV from Arnold's output list and delete its node."""
    try:
        import maya.cmds as cmds  # noqa: PLC0415

        result = _remove_aov(cmds, aov=aov or "")
        return maya_success(
            "Removed AOV {}; {} AOV(s) remain".format(result["removed"]["name"], result["remaining"]),
            removed=result["removed"],
            remaining=result["remaining"],
        )
    except RenderSetupContractError as exc:
        return maya_error(
            "Invalid AOV removal",
            str(exc),
            possible_solutions=[
                "Use list_aovs to get the exact AOV name.",
                "Prefer set_aov_enabled(enabled=false) when you may need it later.",
            ],
        )
    except ImportError:
        return maya_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return maya_from_exception(exc, message="Failed to remove AOV")


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`remove_aov`."""
    return remove_aov(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
