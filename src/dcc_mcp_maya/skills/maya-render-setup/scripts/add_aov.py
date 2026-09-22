"""Create an Arnold AOV and wire it into the render options."""

from __future__ import annotations

from typing import Optional

from dcc_mcp_core.skill import skill_entry

from dcc_mcp_maya.api import maya_error, maya_from_exception, maya_success
from dcc_mcp_maya.render_setup import AOV_TYPES, RenderSetupContractError
from dcc_mcp_maya.render_setup import add_aov as _add_aov


def add_aov(
    name: Optional[str] = None,
    aov_type: Optional[str] = None,
    node_name: Optional[str] = None,
) -> dict:
    """Add an AOV to Arnold's output list."""
    try:
        import maya.cmds as cmds  # noqa: PLC0415

        result = _add_aov(cmds, name=name or "", aov_type=aov_type, node_name=node_name)
        return maya_success(
            "Added AOV {} at aovList[{}]".format(result["aov"]["name"], result["index"]),
            aov=result["aov"],
            index=result["index"],
            prompt=(
                "Disable instead of deleting when you only want to skip it this render: "
                "set_aov_enabled. Group outputs for comp with plan_comp_outputs."
            ),
        )
    except RenderSetupContractError as exc:
        return maya_error(
            "Invalid AOV request",
            str(exc),
            possible_solutions=[
                "aov_type must be one of: " + ", ".join(sorted(AOV_TYPES)),
                "AOV names are unique; use set_aov_enabled to toggle an existing one.",
                "Arnold (mtoa) must be loadable - open Render Settings once if the render options node is missing.",
            ],
        )
    except ImportError:
        return maya_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return maya_from_exception(exc, message="Failed to add AOV")


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`add_aov`."""
    return add_aov(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
