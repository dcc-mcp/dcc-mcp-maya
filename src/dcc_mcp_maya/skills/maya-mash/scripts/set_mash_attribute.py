"""Set an attribute on a MASH node."""
from dcc_mcp_core import error_result, success_result


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
        return error_result(
            "Missing required parameters",
            "'node', 'attribute', and 'value' are all required",
        )

    if not cmds.objExists(node):
        return error_result(
            "Node not found",
            "Node '{}' does not exist".format(node),
            prompt="Use list_networks to find valid MASH node names.",
        )

    try:
        attr_path = "{}.{}".format(node, attribute)
        cmds.setAttr(attr_path, value)
        return success_result(
            "Set {}.{} = {}".format(node, attribute, value),
            prompt="Render or playback to see MASH network changes.",
            node=node,
            attribute=attribute,
            value=value,
        )
    except Exception as exc:
        return error_result(
            "Failed to set MASH attribute",
            str(exc),
            prompt="Check attribute name spelling and value type.",
        )
