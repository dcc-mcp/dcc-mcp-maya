"""Delete a MASH network by waiter node name."""

# Import future modules
from __future__ import annotations

# Import local modules
from dcc_mcp_core.skill import skill_entry, skill_error, skill_exception, skill_success

from dcc_mcp_maya.api import validate_node_exists


def delete_network(waiter: str) -> dict:
    """Delete a MASH network.

    Args:
        waiter: MASH_Waiter node name that identifies the network.

    Returns:
        ToolResult dict.
    """
    try:
        import maya.cmds as cmds  # noqa: PLC0415

        err = validate_node_exists(cmds, waiter)
        if err:
            return err

        import MASH.api as mapi  # noqa: PLC0415

        mash = mapi.Network(waiter)
        mash.deleteNetwork()
        return skill_success(
            "Deleted MASH network '{}'".format(waiter),
            prompt="Use list_networks to verify deletion.",
            waiter=waiter,
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return skill_exception(exc, message="Failed to delete MASH network")


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`delete_network`."""
    return delete_network(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
