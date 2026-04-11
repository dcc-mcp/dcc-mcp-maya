"""Add a MASH node to an existing network."""

# Import local modules
from dcc_mcp_core.skill import skill_error, skill_success


def run(params):
    """Add a MASH node to an existing MASH network.

    Args:
        params: dict with keys:
            - waiter (str, required): MASH_Waiter node that identifies the network.
            - node_type (str, required): MASH node type, e.g. "MASH_Random", "MASH_Distribute",
              "MASH_Dynamics", "MASH_Spring", "MASH_Curve", "MASH_Signal", "MASH_Offset".

    Returns:
        ActionResultModel
    """
    import maya.cmds as cmds

    waiter = params.get("waiter")
    node_type = params.get("node_type")

    if not waiter or not node_type:
        return skill_error(
            "Missing required parameters",
            "Both 'waiter' and 'node_type' are required",
        )

    if not cmds.objExists(waiter):
        return skill_error(
            "Waiter node not found",
            "MASH_Waiter node '{}' does not exist".format(waiter),
            prompt="Use list_networks to find valid waiter names.",
        )

    try:
        import MASH.api as mapi

        mash = mapi.Network(waiter)
        new_node = mash.addNode(node_type)
        return skill_success(
            "Added {} node to network '{}'".format(node_type, waiter),
            prompt="Use set_mash_attribute to configure the new node.",
            node_name=new_node,
            node_type=node_type,
            waiter=waiter,
        )
    except Exception as exc:
        return skill_error(
            "Failed to add MASH node",
            str(exc),
            prompt="Valid node types include: MASH_Random, MASH_Distribute, MASH_Dynamics.",
        )
