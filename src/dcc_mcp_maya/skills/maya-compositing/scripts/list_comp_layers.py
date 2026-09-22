"""List the layers currently connected into a comp stack."""

from __future__ import annotations

from typing import Optional

from dcc_mcp_core.skill import skill_entry

from dcc_mcp_maya.api import maya_error, maya_from_exception, maya_success
from dcc_mcp_maya.compositing import CompositingContractError
from dcc_mcp_maya.compositing import list_layers as _list_layers


def list_comp_layers(stack: Optional[str] = None) -> dict:
    """Describe a stack's layers, in bottom-to-top order."""
    try:
        import maya.cmds as cmds  # noqa: PLC0415

        result = _list_layers(cmds, stack=stack or "")
        return maya_success(
            "{} has {} layer(s)".format(result["stack"], result["count"]),
            **result,
        )
    except CompositingContractError as exc:
        return maya_error(
            "Invalid comp stack lookup",
            str(exc),
            possible_solutions=[
                "stack must be an existing layeredTexture node.",
                "Create one with create_layer_stack first.",
            ],
        )
    except ImportError:
        return maya_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return maya_from_exception(exc, message="Failed to list comp layers")


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`list_comp_layers`."""
    return list_comp_layers(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
