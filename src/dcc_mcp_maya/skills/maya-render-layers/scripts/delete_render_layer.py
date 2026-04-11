"""Delete a render layer from the scene."""

# Import future modules
from __future__ import annotations

# Import local modules
from dcc_mcp_core.skill import skill_entry, skill_error, skill_exception, skill_success

# Import built-in modules


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

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if layer_name == "defaultRenderLayer":
            return skill_error(
                "Cannot delete defaultRenderLayer",
                "The defaultRenderLayer is protected and cannot be removed",
            )

        if not cmds.objExists(layer_name):
            return skill_error(
                "Render layer not found: {}".format(layer_name),
                "'{}' does not exist".format(layer_name),
            )

        if cmds.objectType(layer_name) != "renderLayer":
            return skill_error(
                "Not a render layer: {}".format(layer_name),
                "'{}' is of type '{}'".format(layer_name, cmds.objectType(layer_name)),
            )

        # Switch to defaultRenderLayer if this is the current layer
        current = cmds.editRenderLayerGlobals(query=True, currentRenderLayer=True)
        if current == layer_name:
            cmds.editRenderLayerGlobals(currentRenderLayer="defaultRenderLayer")

        cmds.delete(layer_name)

        return skill_success(
            "Deleted render layer '{}'".format(layer_name),
            layer_name=layer_name,
            prompt="Use list_render_layers to confirm deletion.",
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return skill_exception(exc, message="Failed to delete render layer '{}'".format(layer_name))


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`delete_render_layer`."""
    return delete_render_layer(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main
    run_main(main)
