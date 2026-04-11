"""Add a MASH node to an existing network."""

# Import future modules
from __future__ import annotations

# Import local modules
from dcc_mcp_core.skill import skill_entry, skill_error, skill_exception, skill_success

from dcc_mcp_maya.api import validate_node_exists


def add_node(
    waiter: str,
    node_type: str,
) -> dict:
    """Add a MASH node to an existing MASH network.

    Args:
        waiter: MASH_Waiter node that identifies the network.
        node_type: MASH node type, e.g. "MASH_Random", "MASH_Distribute",
            "MASH_Dynamics", "MASH_Spring", "MASH_Curve", "MASH_Signal", "MASH_Offset".

    Returns:
        ActionResultModel dict with ``context.node_name``.
    """
    try:
        import maya.cmds as cmds  # noqa: PLC0415

        err = validate_node_exists(cmds, waiter)
        if err:
            return err

        import MASH.api as mapi  # noqa: PLC0415

        mash = mapi.Network(waiter)
        new_node = mash.addNode(node_type)
        return skill_success(
            "Added {} node to network '{}'".format(node_type, waiter),
            prompt="Use set_mash_attribute to configure the new node.",
            node_name=new_node,
            node_type=node_type,
            waiter=waiter,
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return skill_exception(
            exc,
            message="Failed to add MASH node",
            prompt="Valid node types include: MASH_Random, MASH_Distribute, MASH_Dynamics.",
        )


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`add_node`."""
    return add_node(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
