"""Enable or disable an existing Arnold AOV."""

from __future__ import annotations

from typing import Optional

from dcc_mcp_core.skill import skill_entry

from dcc_mcp_maya.api import maya_error, maya_from_exception, maya_success
from dcc_mcp_maya.render_setup import RenderSetupContractError
from dcc_mcp_maya.render_setup import set_aov_enabled as _set_enabled


def set_aov_enabled(aov: Optional[str] = None, enabled: bool = True) -> dict:
    """Toggle an AOV without disconnecting it."""
    try:
        import maya.cmds as cmds  # noqa: PLC0415

        result = _set_enabled(cmds, aov=aov or "", enabled=enabled)
        return maya_success(
            "AOV {} is now {}".format(result["aov"]["name"], "enabled" if enabled else "disabled"),
            aov=result["aov"],
            enabled=result["enabled"],
        )
    except RenderSetupContractError as exc:
        return maya_error(
            "Invalid AOV toggle",
            str(exc),
            possible_solutions=[
                "Use list_aovs to get the exact AOV name (not the Maya node name).",
                "Create it first with add_aov.",
            ],
        )
    except ImportError:
        return maya_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return maya_from_exception(exc, message="Failed to toggle AOV")


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`set_aov_enabled`."""
    return set_aov_enabled(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
