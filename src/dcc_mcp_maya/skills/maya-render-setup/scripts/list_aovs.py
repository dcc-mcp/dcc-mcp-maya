"""List the AOVs wired into Arnold's render options."""

from __future__ import annotations

from dcc_mcp_core.skill import skill_entry

from dcc_mcp_maya.api import maya_error, maya_from_exception, maya_success
from dcc_mcp_maya.render_setup import RenderSetupContractError
from dcc_mcp_maya.render_setup import list_aovs as _list_aovs


def list_aovs() -> dict:
    """Report every AOV currently connected to ``aovList``."""
    try:
        import maya.cmds as cmds  # noqa: PLC0415

        result = _list_aovs(cmds)
        return maya_success(
            "Found {} AOV(s)".format(result["count"]),
            aovs=result["aovs"],
            count=result["count"],
            options_node=result["options_node"],
        )
    except RenderSetupContractError as exc:
        return maya_error(
            "AOVs are unavailable",
            str(exc),
            possible_solutions=[
                "Load Arnold (mtoa); AOVs are Arnold-specific.",
                "Open the Render Settings window once to create the Arnold options node.",
            ],
        )
    except ImportError:
        return maya_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return maya_from_exception(exc, message="Failed to list AOVs")


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`list_aovs`."""
    return list_aovs(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
