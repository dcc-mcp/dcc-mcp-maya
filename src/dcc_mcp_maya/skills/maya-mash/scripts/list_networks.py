"""List all MASH networks in the scene."""

# Import local modules
from dcc_mcp_core.skill import skill_error, skill_success


def run(params):  # noqa: ARG001
    """List all MASH networks present in the current scene.

    Args:
        params: dict (unused — no parameters required)

    Returns:
        ActionResultModel
    """
    try:
        import maya.cmds as cmds

        # MASH waiter nodes are the root of each network
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
        return skill_error("Failed to list MASH networks", str(exc))
