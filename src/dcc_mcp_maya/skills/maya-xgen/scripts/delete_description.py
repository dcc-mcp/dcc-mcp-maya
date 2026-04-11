"""Delete an XGen description from the scene."""

# Import local modules
from dcc_mcp_maya.api import maya_error, maya_success


def run(params):
    """Delete an XGen description by collection and description name.

    Args:
        params: dict with keys:
            - collection (str, required): XGen collection name.
            - description (str, required): Description name to delete.

    Returns:
        ActionResultModel
    """
    collection = params.get("collection")
    description = params.get("description")

    if not collection or not description:
        return maya_error(
            "Missing required parameters",
            "Both 'collection' and 'description' are required",
        )

    try:
        import xgenm as xg

        if description not in xg.descriptions(collection):
            return maya_error(
                "Description not found",
                "'{}' not found in collection '{}'".format(description, collection),
                prompt="Use list_descriptions to view available descriptions.",
            )

        xg.deleteDescription(collection, description)
        return maya_success(
            "Deleted XGen description '{}'".format(description),
            prompt="Use list_descriptions to verify deletion.",
            collection=collection,
            description=description,
        )
    except Exception as exc:
        return maya_error("Failed to delete XGen description", str(exc))
