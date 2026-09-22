"""Create a colour/utility node for a comp network."""

from __future__ import annotations

from typing import Optional

from dcc_mcp_core.skill import skill_entry

from dcc_mcp_maya.api import maya_error, maya_from_exception, maya_success
from dcc_mcp_maya.compositing import UTILITY_NODES, CompositingContractError
from dcc_mcp_maya.compositing import create_comp_node as _create_comp_node


def create_comp_node(
    node_type: Optional[str] = None,
    name: Optional[str] = None,
    operation: Optional[str] = None,
) -> dict:
    """Create a reverse / multiplyDivide / luminance / clamp / setRange node."""
    try:
        import maya.cmds as cmds  # noqa: PLC0415

        result = _create_comp_node(
            cmds,
            node_type=node_type or "",
            name=name,
            operation=operation,
        )
        return maya_success(
            "Created {} node {}".format(result["node_type"], result["node"]),
            **result,
        )
    except CompositingContractError as exc:
        return maya_error(
            "Invalid comp node request",
            str(exc),
            possible_solutions=[
                "node_type must be one of: " + ", ".join(UTILITY_NODES),
                "operation only applies to multiplyDivide (none/multiply/divide/power).",
            ],
        )
    except ImportError:
        return maya_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return maya_from_exception(exc, message="Failed to create comp node")


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`create_comp_node`."""
    return create_comp_node(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
