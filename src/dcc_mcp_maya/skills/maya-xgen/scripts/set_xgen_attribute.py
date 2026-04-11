"""Set an attribute on an XGen description or modifier."""

# Import local modules
from dcc_mcp_core.skill import skill_error, skill_success


def run(params):
    """Set an XGen attribute value.

    Args:
        params: dict with keys:
            - collection (str, required): XGen collection name.
            - description (str, required): Description name.
            - attribute (str, required): Attribute name (e.g. "density", "length").
            - value (str, required): New value as string (XGen uses string-based attrs).
            - object_name (str, optional): Object context for patch attributes.

    Returns:
        ActionResultModel
    """
    collection = params.get("collection")
    description = params.get("description")
    attribute = params.get("attribute")
    value = params.get("value")

    if not all([collection, description, attribute, value is not None]):
        return skill_error(
            "Missing required parameters",
            "'collection', 'description', 'attribute', and 'value' are all required",
        )

    object_name = params.get("object_name", "")

    try:
        import xgenm as xg

        xg.setAttr(attribute, str(value), collection, description, object_name)
        return skill_success(
            "Set {}.{} = {}".format(description, attribute, value),
            prompt="Use get_xgen_attribute to verify the change.",
            collection=collection,
            description=description,
            attribute=attribute,
            value=str(value),
        )
    except Exception as exc:
        return skill_error("Failed to set XGen attribute", str(exc))
