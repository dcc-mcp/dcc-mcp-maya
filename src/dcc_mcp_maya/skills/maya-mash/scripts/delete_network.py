"""Delete a MASH network by waiter node name."""

# Import local modules
from dcc_mcp_maya.api import maya_error, maya_success


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
        return maya_error("Missing required parameter", "'waiter' is required")

    if not cmds.objExists(waiter):
        return maya_error(
            "Waiter node not found",
            "MASH_Waiter node '{}' does not exist".format(waiter),
            prompt="Use list_networks to find valid waiter node names.",
        )

    try:
        import MASH.api as mapi

        mash = mapi.Network(waiter)
        mash.deleteNetwork()
        return maya_success(
            "Deleted MASH network '{}'".format(waiter),
            prompt="Use list_networks to verify deletion.",
            waiter=waiter,
        )
    except Exception as exc:
        return maya_error("Failed to delete MASH network", str(exc))
