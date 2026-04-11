"""Create a display layer and optionally add objects to it."""

# Import future modules
from __future__ import annotations

# Import built-in modules
from typing import List, Optional

# Import local modules
from dcc_mcp_core.skill import skill_entry, skill_error, skill_exception, skill_success


def create_display_layer(
    name: Optional[str] = None,
    objects: Optional[List[str]] = None,
    visibility: bool = True,
) -> dict:
    """Create a display layer and optionally add objects to it.

    Args:
        name: Name for the new display layer.  If None, Maya generates one.
        objects: List of object names to add to the layer immediately.
        visibility: Initial visibility state of the layer.

    Returns:
        ActionResultModel dict with ``context.layer_name``.
    """
    try:
        import maya.cmds as cmds  # noqa: PLC0415

        kwargs = {"empty": True, "noRecurse": True}
        if name:
            kwargs["name"] = name
        layer_name = cmds.createDisplayLayer(**kwargs)

        if not visibility:
            cmds.setAttr("{}.visibility".format(layer_name), 0)

        added = []
        if objects:
            for obj in objects:
                if cmds.objExists(obj):
                    cmds.editDisplayLayerMembers(layer_name, obj, noRecurse=True)
                    added.append(obj)

        return skill_success(
            "Created display layer '{}'".format(layer_name),
            prompt="Use set_display_layer to add more objects or list_display_layers to see all layers.",
            layer_name=layer_name,
            objects_added=added,
            visibility=visibility,
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return skill_exception(exc, message="Failed to create display layer")


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`create_display_layer`."""
    return create_display_layer(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main
    run_main(main)
