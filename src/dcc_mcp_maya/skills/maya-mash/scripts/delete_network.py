"""Delete a MASH network by waiter node name."""
from dcc_mcp_core import error_result, success_result


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
        return error_result("Missing required parameter", "'waiter' is required")

    if not cmds.objExists(waiter):
        return error_result(
            "Waiter node not found",
            "MASH_Waiter node '{}' does not exist".format(waiter),
            prompt="Use list_networks to find valid waiter node names.",
        )

    try:
        import MASH.api as mapi

        mash = mapi.Network(waiter)
        mash.deleteNetwork()
        return success_result(
            "Deleted MASH network '{}'".format(waiter),
            prompt="Use list_networks to verify deletion.",
            waiter=waiter,
        )
    except Exception as exc:
        return error_result("Failed to delete MASH network", str(exc))
