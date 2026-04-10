"""Convert the current selection to a different component type."""
from dcc_mcp_core import error_result, success_result

_CONVERT_FLAGS = {
    "vertex": {"toVertex": True},
    "edge": {"toEdge": True},
    "face": {"toFace": True},
    "uv": {"toUV": True},
    "object": {"toObject": True},
    "shell": {"toShell": True},
}


def run(params):
    """Convert selection to a different component type.

    Args:
        params: dict with keys:
            - target (str, required): Component type to convert to.
              One of: "vertex", "edge", "face", "uv", "object", "shell".

    Returns:
        ActionResultModel
    """
    import maya.cmds as cmds

    target = params.get("target", "").lower()
    if target not in _CONVERT_FLAGS:
        return error_result(
            "Invalid target type",
            "'{}' is not a valid target. Choose from: {}".format(
                target, ", ".join(sorted(_CONVERT_FLAGS.keys()))
            ),
        )

    try:
        flags = _CONVERT_FLAGS[target]
        cmds.ConvertSelectionToVertices() if target == "vertex" else None
        # Use polyListComponentConversion for component types
        current = cmds.ls(selection=True) or []
        if not current:
            return error_result(
                "Nothing selected",
                "Select objects or components before converting",
            )

        if target == "object":
            cmds.select(cmds.ls(selection=True, objectsOnly=True))
        else:
            converted = cmds.polyListComponentConversion(current, **flags) or []
            if converted:
                cmds.select(converted)

        result = cmds.ls(selection=True, flatten=True) or []
        return success_result(
            "Converted selection to {} ({} items)".format(target, len(result)),
            prompt="Use grow_selection or shrink_selection to refine the component selection.",
            target=target,
            count=len(result),
            selection=result,
        )
    except Exception as exc:
        return error_result("Failed to convert selection", str(exc))
