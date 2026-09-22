"""Disconnect one layer from a comp stack."""

from __future__ import annotations

from typing import Optional

from dcc_mcp_core.skill import skill_entry

from dcc_mcp_maya.api import maya_error, maya_from_exception, maya_success
from dcc_mcp_maya.compositing import CompositingContractError
from dcc_mcp_maya.compositing import remove_layer as _remove_layer


def remove_comp_layer(stack: Optional[str] = None, index: Optional[int] = None) -> dict:
    """Remove a layer; the source node itself is left untouched."""
    try:
        import maya.cmds as cmds  # noqa: PLC0415

        result = _remove_layer(cmds, stack=stack or "", index=index)
        return maya_success(
            "Removed layer {} from {}".format(result["removed_index"], result["stack"]),
            **result,
        )
    except CompositingContractError as exc:
        return maya_error(
            "Invalid comp layer removal",
            str(exc),
            possible_solutions=[
                "Use list_comp_layers to see which indices are occupied.",
                "Only the connection is removed; the source node is kept.",
            ],
        )
    except ImportError:
        return maya_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return maya_from_exception(exc, message="Failed to remove comp layer")


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`remove_comp_layer`."""
    return remove_comp_layer(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
