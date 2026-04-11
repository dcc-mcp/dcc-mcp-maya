"""Create an XGen description on a mesh."""

# Import local modules
from dcc_mcp_maya.api import maya_error, maya_success


def run(params):
    """Create an XGen description (hair/fur) on a bound mesh.

    Args:
        params: dict with keys:
            - mesh (str, required): The mesh transform to bind XGen to.
            - collection (str, optional): XGen collection name. Defaults to "xgenCollection1".
            - description (str, optional): Description name. Defaults to "description1".
            - primitive (str, optional): Primitive type: "SplinePrimitive" (default), "CardPrimitive", "SpherePrimitive".

    Returns:
        ActionResultModel
    """
    import maya.cmds as cmds

    mesh = params.get("mesh")
    if not mesh:
        return maya_error("Missing required parameter", "'mesh' is required")

    collection = params.get("collection", "xgenCollection1")
    description = params.get("description", "description1")
    primitive = params.get("primitive", "SplinePrimitive")

    try:
        if not cmds.objExists(mesh):
            return maya_error(
                "Mesh not found",
                "Object '{}' does not exist in the scene".format(mesh),
                prompt="Use list_objects to find valid mesh names.",
            )

        # XGen Python API
        import xgenm as xg

        palette = xg.createPalette(collection)
        desc = xg.createDescription(palette, description, primitive, mesh)
        return maya_success(
            "Created XGen description '{}' on '{}'".format(desc, mesh),
            prompt="Use set_xgen_attribute to configure density, length, and other parameters.",
            collection=palette,
            description=desc,
            mesh=mesh,
            primitive=primitive,
        )
    except Exception as exc:
        return maya_error(
            "Failed to create XGen description",
            str(exc),
            prompt="Ensure XGen plugin is loaded: cmds.loadPlugin('xgenToolkit').",
        )
