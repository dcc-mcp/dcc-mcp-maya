"""Delete an XGen description from the scene."""
from dcc_mcp_core import error_result, success_result


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
        return error_result(
            "Missing required parameters",
            "Both 'collection' and 'description' are required",
        )

    try:
        import xgenm as xg

        if description not in xg.descriptions(collection):
            return error_result(
                "Description not found",
                "'{}' not found in collection '{}'".format(description, collection),
                prompt="Use list_descriptions to view available descriptions.",
            )

        xg.deleteDescription(collection, description)
        return success_result(
            "Deleted XGen description '{}'".format(description),
            prompt="Use list_descriptions to verify deletion.",
            collection=collection,
            description=description,
        )
    except Exception as exc:
        return error_result("Failed to delete XGen description", str(exc))
