"""Assign an object to an existing display layer."""

# Import future modules
from __future__ import annotations

# Import built-in modules
from typing import List

# Import local modules
from dcc_mcp_core.skill import skill_entry, skill_error, skill_exception, skill_success


def set_display_layer(layer_name: str, objects: List[str]) -> dict:
    """Assign one or more objects to an existing display layer.

    Args:
        layer_name: Name of the target display layer.
        objects: List of object names to assign.

    Returns:
        ActionResultModel dict with ``context.assigned``.
    """
    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not cmds.objExists(layer_name):
            return skill_error(
                "Display layer not found",
                "Layer '{}' does not exist in the scene".format(layer_name),
            )

        assigned = []
        missing = []
        for obj in objects:
            if cmds.objExists(obj):
                cmds.editDisplayLayerMembers(layer_name, obj, noRecurse=True)
                assigned.append(obj)
            else:
                missing.append(obj)

        msg = "Assigned {} object(s) to layer '{}'".format(len(assigned), layer_name)
        if missing:
            msg += "; {} not found: {}".format(len(missing), missing)

        return skill_success(
            msg,
            prompt="Use list_display_layers to verify the layer membership.",
            layer_name=layer_name,
            assigned=assigned,
            missing=missing,
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return skill_exception(exc, message="Failed to assign objects to layer '{}'".format(layer_name))


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`set_display_layer`."""
    return set_display_layer(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main
    run_main(main)
