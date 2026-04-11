"""Delete a MASH network by waiter node name."""

# Import local modules
from dcc_mcp_core.skill import skill_error, skill_success


def run(params):
    """Delete a MASH network.

    Args:
        params: dict with keys:
            - waiter (str, required): MASH_Waiter node name that identifies the network.

    Returns:
        ActionResultModel
    """
    import maya.cmds as cmds

    waiter = params.get("waiter")
    if not waiter:
        return skill_error("Missing required parameter", "'waiter' is required")

    if not cmds.objExists(waiter):
        return skill_error(
            "Waiter node not found",
            "MASH_Waiter node '{}' does not exist".format(waiter),
            prompt="Use list_networks to find valid waiter node names.",
        )

    try:
        import MASH.api as mapi

        mash = mapi.Network(waiter)
        mash.deleteNetwork()
        return skill_success(
            "Deleted MASH network '{}'".format(waiter),
            prompt="Use list_networks to verify deletion.",
            waiter=waiter,
        )
    except Exception as exc:
        return skill_error("Failed to delete MASH network", str(exc))
