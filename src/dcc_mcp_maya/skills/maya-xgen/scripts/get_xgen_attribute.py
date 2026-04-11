"""Get an attribute value from an XGen description."""

# Import local modules
from dcc_mcp_maya.api import maya_error, maya_success


def run(params):
    """Get an XGen attribute value.

    Args:
        params: dict with keys:
            - collection (str, required): XGen collection name.
            - description (str, required): Description name.
            - attribute (str, required): Attribute name.
            - object_name (str, optional): Object context.

    Returns:
        ActionResultModel
    """
    collection = params.get("collection")
    description = params.get("description")
    attribute = params.get("attribute")

    if not all([collection, description, attribute]):
        return maya_error(
            "Missing required parameters",
            "'collection', 'description', and 'attribute' are all required",
        )

    object_name = params.get("object_name", "")

    try:
        import xgenm as xg

        value = xg.getAttr(attribute, collection, description, object_name)
        return maya_success(
            "{}.{} = {}".format(description, attribute, value),
            prompt="Use set_xgen_attribute to modify this value.",
            collection=collection,
            description=description,
            attribute=attribute,
            value=value,
        )
    except Exception as exc:
        return maya_error("Failed to get XGen attribute", str(exc))
