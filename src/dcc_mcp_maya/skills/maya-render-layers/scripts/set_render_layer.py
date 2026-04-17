"""Assign an object to an existing render layer."""

# Import future modules
from __future__ import annotations

# Import local modules
from dcc_mcp_core.skill import skill_entry, skill_error, skill_success

from dcc_mcp_maya.api import validate_node_exists

# Import built-in modules


def set_render_layer(
    object_name: str,
    layer_name: str,
) -> dict:
    """Assign an object to an existing render layer.

    Args:
        object_name: Name of the object to assign.
        layer_name: Name of the target render layer.

    Returns:
        ToolResult dict with ``context.object_name`` and
        ``context.layer_name``.
    """

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        err = validate_node_exists(cmds, object_name)
        if err:
            return err

        err = validate_node_exists(cmds, layer_name)
        if err:
            return err

        if cmds.objectType(layer_name) != "renderLayer":
            return skill_error(
                "Not a render layer: {}".format(layer_name),
                "'{}' is of type '{}', expected 'renderLayer'".format(layer_name, cmds.objectType(layer_name)),
            )

        cmds.editRenderLayerMembers(layer_name, object_name, noRecurse=True)

        return skill_success(
            "Assigned '{}' to render layer '{}'".format(object_name, layer_name),
            object_name=object_name,
            layer_name=layer_name,
            prompt="Check the result with list_render_layers or use related actions to continue.",
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return skill_error(
            "Failed to assign '{}' to render layer '{}'".format(object_name, layer_name),
            str(exc),
        )


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`set_render_layer`."""
    return set_render_layer(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
