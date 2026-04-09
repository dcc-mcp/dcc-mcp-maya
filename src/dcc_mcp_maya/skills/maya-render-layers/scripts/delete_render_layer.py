"""Delete a render layer from the scene."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging

logger = logging.getLogger(__name__)


def delete_render_layer(layer_name: str) -> dict:
    """Delete a render layer from the scene.

    The built-in ``defaultRenderLayer`` cannot be deleted.  Any objects that
    were members of the layer are moved back to the default render layer
    automatically by Maya.

    Args:
        layer_name: Name of the render layer to delete.

    Returns:
        ActionResultModel dict with ``context.layer_name``.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if layer_name == "defaultRenderLayer":
            return error_result(
                "Cannot delete defaultRenderLayer",
                "The defaultRenderLayer is protected and cannot be removed",
            ).to_dict()

        if not cmds.objExists(layer_name):
            return error_result(
                "Render layer not found: {}".format(layer_name),
                "'{}' does not exist".format(layer_name),
            ).to_dict()

        if cmds.objectType(layer_name) != "renderLayer":
            return error_result(
                "Not a render layer: {}".format(layer_name),
                "'{}' is of type '{}'".format(layer_name, cmds.objectType(layer_name)),
            ).to_dict()

        # Switch to defaultRenderLayer if this is the current layer
        current = cmds.editRenderLayerGlobals(query=True, currentRenderLayer=True)
        if current == layer_name:
            cmds.editRenderLayerGlobals(currentRenderLayer="defaultRenderLayer")

        cmds.delete(layer_name)

        return success_result(
            "Deleted render layer '{}'".format(layer_name),
            layer_name=layer_name,
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("delete_render_layer failed")
        return error_result("Failed to delete render layer '{}'".format(layer_name), str(exc)).to_dict()


def main(**kwargs):
    return delete_render_layer(**kwargs)


if __name__ == "__main__":
    import json

    result = delete_render_layer()
    print(json.dumps(result))
