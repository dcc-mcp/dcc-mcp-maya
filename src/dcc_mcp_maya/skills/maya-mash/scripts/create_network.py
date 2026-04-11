"""Create a MASH network for an object."""

# Import local modules
from dcc_mcp_maya.api import maya_error, maya_success


def run(params):
    """Create a MASH network for an object.

    Args:
        params: dict with keys:
            - object_name (str, required): Object to use as the MASH instancer source.
            - network_name (str, optional): Name for the MASH network. Auto-generated if omitted.
            - geometry_type (str, optional): "Instancer" (default) or "Repro".

    Returns:
        ActionResultModel
    """
    import maya.cmds as cmds

    object_name = params.get("object_name")
    if not object_name:
        return maya_error("Missing required parameter", "'object_name' is required")

    if not cmds.objExists(object_name):
        return maya_error(
            "Object not found",
            "Object '{}' does not exist".format(object_name),
            prompt="Use list_objects to find valid object names.",
        )

    network_name = params.get("network_name", "")
    geometry_type = params.get("geometry_type", "Instancer")

    try:
        import MASH.api as mapi

        mash = mapi.Network()
        if network_name:
            mash.createNetwork(object_name, networkName=network_name, geometryType=geometry_type)
        else:
            mash.createNetwork(object_name, geometryType=geometry_type)

        return maya_success(
            "Created MASH network for '{}'".format(object_name),
            prompt="Use add_node to add MASH nodes like Distribute, Random, or Dynamics.",
            network_name=mash.meshName,
            instancer=mash.instancer,
            waiter=mash.waiter,
        )
    except Exception as exc:
        return maya_error(
            "Failed to create MASH network",
            str(exc),
            prompt="Ensure MASH plugin is loaded: cmds.loadPlugin('MASH').",
        )
