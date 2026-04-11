"""Set an attribute on a MASH node."""

# Import local modules
from dcc_mcp_core.skill import skill_error, skill_success


def run(params):
    """Set an attribute value on a MASH node.

    Args:
        params: dict with keys:
            - node (str, required): MASH node name.
            - attribute (str, required): Attribute name (e.g. "amplitudeX", "pointCount").
            - value (required): New value (numeric or string).

    Returns:
        ActionResultModel
    """
    import maya.cmds as cmds

    node = params.get("node")
    attribute = params.get("attribute")
    value = params.get("value")

    if not node or not attribute or value is None:
        return skill_error(
            "Missing required parameters",
            "'node', 'attribute', and 'value' are all required",
        )

    if not cmds.objExists(node):
        return skill_error(
            "Node not found",
            "Node '{}' does not exist".format(node),
            prompt="Use list_networks to find valid MASH node names.",
        )

    try:
        attr_path = "{}.{}".format(node, attribute)
        cmds.setAttr(attr_path, value)
        return skill_success(
            "Set {}.{} = {}".format(node, attribute, value),
            prompt="Render or playback to see MASH network changes.",
            node=node,
            attribute=attribute,
            value=value,
        )
    except Exception as exc:
        return skill_error(
            "Failed to set MASH attribute",
            str(exc),
            prompt="Check attribute name spelling and value type.",
        )
