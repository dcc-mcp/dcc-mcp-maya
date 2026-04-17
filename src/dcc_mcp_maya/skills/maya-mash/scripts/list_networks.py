"""List all MASH networks in the scene."""

# Import future modules
from __future__ import annotations

# Import local modules
from dcc_mcp_core.skill import skill_entry, skill_exception, skill_success


def list_networks() -> dict:
    """List all MASH networks present in the current scene.

    Returns:
        ToolResult dict with ``context.networks`` and ``context.count``.
    """
    try:
        import maya.cmds as cmds  # noqa: PLC0415

        waiter_nodes = cmds.ls(type="MASH_Waiter") or []
        networks = []
        for waiter in waiter_nodes:
            instancer_conn = cmds.listConnections(waiter + ".instancerMessage", source=False) or []
            networks.append(
                {
                    "waiter": waiter,
                    "instancers": instancer_conn,
                }
            )

        return skill_success(
            "Found {} MASH network(s)".format(len(networks)),
            prompt="Use add_node or set_mash_attribute to modify networks.",
            networks=networks,
            count=len(networks),
        )
    except Exception as exc:
        return skill_exception(exc, message="Failed to list MASH networks")


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`list_networks`."""
    return list_networks(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
